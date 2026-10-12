"""Read PE headers/imports on disk. Never load or execute a target image."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct


def inspect(path):
    data = path.read_bytes()
    warnings = []

    def unpack(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(data):
            raise ValueError(f"Field outside file at {offset:#x}")
        return struct.unpack_from(fmt, data, offset)[0]

    if data[:2] != b"MZ":
        raise ValueError("Missing MZ header")
    pe = unpack("<I", 0x3c)
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Missing PE signature")
    machine = unpack("<H", pe + 4)
    section_count = unpack("<H", pe + 6)
    optional_size = unpack("<H", pe + 20)
    if not 0 < section_count <= 96:
        raise ValueError("Unsupported section count")
    optional = pe + 24
    magic = unpack("<H", optional)
    if magic not in (0x10b, 0x20b):
        raise ValueError("Unsupported optional header")
    is64 = magic == 0x20b
    directory_offset = 112 if is64 else 96
    directory_count_offset = 108 if is64 else 92
    if optional_size < directory_offset:
        raise ValueError("Truncated optional header")
    directory_count = unpack("<I", optional + directory_count_offset)
    header_size = unpack("<I", optional + 60)
    sections = []
    for index in range(section_count):
        offset = optional + optional_size + index * 40
        if offset + 40 > len(data):
            raise ValueError("Truncated section table")
        name = data[offset:offset + 8].split(b"\0", 1)[0].decode("ascii", "replace")
        raw_size = unpack("<I", offset + 16)
        raw_offset = unpack("<I", offset + 20)
        if raw_size and raw_offset + raw_size > len(data):
            warnings.append(f"Section {name}: truncated raw data")
        raw = data[raw_offset:raw_offset + raw_size]
        counts = Counter(raw)
        entropy = -sum((n / len(raw)) * math.log2(n / len(raw)) for n in counts.values()) if raw else 0
        sections.append({
            "name": name,
            "virtual_size": unpack("<I", offset + 8),
            "rva": unpack("<I", offset + 12),
            "raw_size": raw_size,
            "raw_offset": raw_offset,
            "characteristics": f"0x{unpack('<I', offset + 36):08x}",
            "entropy_bits_per_byte": round(entropy, 4),
        })

    def file_offset(rva):
        if 0 <= rva < min(header_size, len(data)):
            return rva
        for section in sections:
            delta = rva - section["rva"]
            if 0 <= delta < section["raw_size"]:
                result = section["raw_offset"] + delta
                if result < len(data):
                    return result
        raise ValueError(f"RVA has no on-disk mapping: {rva:#x}")

    def cstring(rva):
        start = file_offset(rva)
        end = data.find(b"\0", start, min(start + 4096, len(data)))
        if end < 0:
            raise ValueError("Unterminated import name")
        return data[start:end].decode("ascii", "replace")

    imports = []
    imports_complete = True
    import_rva = import_size = 0
    if directory_count > 1 and optional_size >= directory_offset + 16:
        import_rva = unpack("<I", optional + directory_offset + 8)
        import_size = unpack("<I", optional + directory_offset + 12)
    if import_rva:
        try:
            terminated = False
            for index in range(min(import_size // 20, 4096)):
                descriptor = file_offset(import_rva + index * 20)
                fields = struct.unpack_from("<IIIII", data, descriptor)
                if not any(fields):
                    terminated = True
                    break
                original_thunk, _, _, name_rva, first_thunk = fields
                dll = cstring(name_rva)
                symbols = []
                thunk_rva = original_thunk or first_thunk
                width, fmt = (8, "<Q") if is64 else (4, "<I")
                ordinal_flag = 1 << (width * 8 - 1)
                if not thunk_rva:
                    raise ValueError("Import descriptor without thunk table")
                for symbol_index in range(65536):
                    value = unpack(fmt, file_offset(thunk_rva + symbol_index * width))
                    if not value:
                        break
                    symbols.append(f"ordinal:{value & 0xffff}" if value & ordinal_flag else cstring(value + 2))
                else:
                    raise ValueError("Unterminated thunk table")
                imports.append({"module": dll, "symbols": symbols})
            if not terminated:
                raise ValueError("Unterminated or zero-sized import descriptor table")
        except (ValueError, struct.error) as error:
            imports_complete = False
            warnings.append(f"Import parse incomplete: {error}")
    return {
        "path": str(path.resolve()), "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "machine": {0x8664: "AMD64/x86-64", 0x14c: "I386/x86"}.get(machine, f"0x{machine:04x}"),
        "format": "PE32+" if is64 else "PE32",
        "subsystem": {1: "Native", 2: "Windows GUI", 3: "Windows CUI"}.get(unpack("<H", optional + 68), "Other"),
        "entrypoint_rva": unpack("<I", optional + 16),
        "sections": sections, "imports": imports,
        "imports_complete": imports_complete, "warnings": warnings,
        "limitations": "Static headers and ordinary import table only. Dynamic/delay imports, protected code, runtime calls and protocols were not analyzed. Entropy does not prove encryption or packing.",
    }


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("paths", nargs="+", type=Path)
args = parser.parse_args()
results = []
for path in args.paths:
    try:
        item = inspect(path)
    except (OSError, ValueError, struct.error) as error:
        item = {"path": str(path), "error": str(error)}
    results.append(item)
    print(json.dumps({
        "file": path.name, "machine": item.get("machine"),
        "subsystem": item.get("subsystem"),
        "sections": len(item.get("sections", [])),
        "modules": [entry["module"] for entry in item.get("imports", [])],
        "import_symbols": sum(len(entry["symbols"]) for entry in item.get("imports", [])),
        "warnings": item.get("warnings", []), "error": item.get("error"),
    }))
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({
    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
    "method": "Read-only static PE parser based on Microsoft PE/COFF specification; no target image loaded or executed.",
    "files": results,
}, indent=2, ensure_ascii=False), encoding="utf-8")
