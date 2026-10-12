"""Read copied driver PE bytes only; never load/execute target images."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parent
path = root / "samples" / "vgk.sys"
data = path.read_bytes()
warnings = []

def field(fmt, off):
    if off < 0 or off + struct.calcsize(fmt) > len(data):
        raise ValueError(f"Out-of-file field: {off:#x}")
    return struct.unpack_from(fmt, data, off)[0]

assert data[:2] == b"MZ"
pe = field("<I", 0x3c)
assert data[pe:pe + 4] == b"PE\0\0"
opt = pe + 24
assert field("<H", opt) == 0x20b
size_opt = field("<H", pe + 20)
assert size_opt >= 112
image_base = field("<Q", opt + 24)
headers_size = field("<I", opt + 60)
sections = []
for i in range(field("<H", pe + 6)):
    off = opt + size_opt + i * 40
    sections.append({
        "name": data[off:off + 8].split(b"\0", 1)[0].decode("ascii", "replace"),
        "rva": field("<I", off + 12), "virtual_size": field("<I", off + 8),
        "raw_offset": field("<I", off + 20), "raw_size": field("<I", off + 16),
        "characteristics": f"0x{field('<I', off + 36):08x}",
    })

def mapping(rva, size=1):
    if size < 0:
        raise ValueError("Negative mapping size")
    if 0 <= rva and rva + size <= min(headers_size, len(data)):
        return rva
    for sec in sections:
        delta = rva - sec["rva"]
        if 0 <= delta and delta + size <= sec["raw_size"]:
            off = sec["raw_offset"] + delta
            if off + size <= len(data):
                return off
    raise ValueError(f"Unmapped RVA range: {rva:#x}+{size:#x}")

def string(rva):
    off = mapping(rva)
    end = data.find(b"\0", off, min(len(data), off + 4096))
    if end < 0:
        raise ValueError("Unterminated PE string")
    mapping(rva, end - off + 1)
    return data[off:end].decode("ascii", "replace")

names = ["export", "import", "resource", "exception", "security", "base_relocation", "debug", "architecture", "global_ptr", "tls", "load_config", "bound_import", "iat", "delay_import", "clr", "reserved"]
directories = []
for i in range(min(16, field("<I", opt + 108), (size_opt - 112) // 8)):
    off = opt + 112 + 8 * i
    value = field("<I", off)
    size = field("<I", off + 4)
    directory = {"index": i, "name": names[i], "value": value, "size": size, "address_kind": "file_offset" if i == 4 else "rva"}
    if value and size:
        try:
            fileoff = value if i == 4 else mapping(value, size)
            if fileoff + size > len(data):
                raise ValueError("Directory extends beyond file")
            directory["file_offset"] = fileoff
        except ValueError as error:
            directory["warning"] = str(error)
    directories.append(directory)

exports = []
ed = directories[0]
if ed["value"]:
    try:
        eoff = mapping(ed["value"], 40)
        ordinal_base = field("<I", eoff + 16)
        function_count, name_count = field("<I", eoff + 20), field("<I", eoff + 24)
        functions, name_table, ordinals = [field("<I", eoff + j) for j in (28, 32, 36)]
        if max(function_count, name_count) > 65536:
            raise ValueError("Unexpected export count")
        export_names = {}
        for i in range(name_count):
            name_rva = field("<I", mapping(name_table + 4 * i, 4))
            ordinal_index = field("<H", mapping(ordinals + 2 * i, 2))
            export_names.setdefault(ordinal_index, []).append(string(name_rva))
        for i in range(function_count):
            rva = field("<I", mapping(functions + 4 * i, 4))
            if not rva:
                continue
            item = {"ordinal": ordinal_base + i, "names": export_names.get(i, []), "rva": rva}
            if ed["value"] <= rva < ed["value"] + ed["size"]:
                item["forwarder"] = string(rva)
            else:
                item["file_offset"] = mapping(rva)
                item["section"] = next((s["name"] for s in sections if s["rva"] <= rva < s["rva"] + max(s["raw_size"], s["virtual_size"])), None)
            exports.append(item)
    except (ValueError, struct.error) as error:
        warnings.append(f"Export parse: {error}")

tls_callbacks = []
td = directories[9]
if td["value"]:
    try:
        toff = mapping(td["value"], 40)
        callback_va = field("<Q", toff + 24)
        if callback_va:
            for i in range(256):
                va = field("<Q", mapping(callback_va - image_base + 8 * i, 8))
                if not va:
                    break
                tls_callbacks.append({"va": va, "rva": va - image_base})
            else:
                warnings.append("TLS callback table exceeded bounded parse")
    except (ValueError, struct.error) as error:
        warnings.append(f"TLS parse: {error}")

exception = directories[3]
exception_summary = None
if exception["value"] and exception["size"]:
    try:
        exoff = mapping(exception["value"], exception["size"])
        records = exception["size"] // 12
        coherent_ranges = 0
        previous_begin = -1
        sorted_begin = True
        entry_records = []
        for i in range(records):
            begin, end, unwind = struct.unpack_from("<III", data, exoff + i * 12)
            sorted_begin = sorted_begin and previous_begin <= begin
            previous_begin = begin
            if begin <= field("<I", opt + 16) < end:
                entry_records.append({"begin_rva": begin, "end_rva": end, "unwind_rva": unwind})
            if 0 < begin < end <= field("<I", opt + 56):
                try:
                    mapping(begin)
                    mapping(unwind)
                    coherent_ranges += 1
                except ValueError:
                    pass
        exception_summary = {"declared_bytes": exception["size"], "size_multiple_of_12": exception["size"] % 12 == 0, "candidate_records": records, "records_passing_minimal_range_mapping_check": coherent_ranges, "nondecreasing_begin_rva": sorted_begin, "records_covering_pe_entrypoint": entry_records, "limitation": "Heuristic byte-range check only. No unwind instruction/code validation or runtime interpretation."}
    except ValueError as error:
        warnings.append(f"Exception parse: {error}")

entry = field("<I", opt + 16)
entry_off = mapping(entry)
result = {
    "collected_at_utc": datetime.now(timezone.utc).isoformat(),
    "path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
    "image_base_preferred": image_base, "image_size_declared": field("<I", opt + 56),
    "coff_timestamp_raw": field("<I", pe + 8),
    "coff_characteristics": f"0x{field('<H', pe + 22):04x}",
    "dll_characteristics": f"0x{field('<H', opt + 70):04x}",
    "entrypoint": {"rva": entry, "file_offset": entry_off, "section": next((s["name"] for s in sections if s["rva"] <= entry < s["rva"] + max(s["raw_size"], s["virtual_size"])), None)},
    "sections": sections, "data_directories": directories, "exports": exports,
    "tls_callbacks": tls_callbacks, "exception_summary": exception_summary, "warnings": warnings,
    "limitations": "Static PE bytes only, no disassembly, loading, execution or protocol analysis. Header flags/names do not establish runtime behavior. No certificate verification in this parser.",
}
output = root / "vgk-static-details.json"
output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
