#!/usr/bin/env python3
"""Read-only inspection of ASAR/package and executable metadata; executes no app."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct

ARCHIVE = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games/Riot Client/RiotClientElectron/resources/app.asar')
UNPACKED = Path(str(ARCHIVE) + '.unpacked')
MAX_HEADER = 32 * 1024 * 1024
MAX_METADATA = 2 * 1024 * 1024
MAX_BINARY = 32 * 1024 * 1024


def parse_header():
    length = ARCHIVE.stat().st_size
    with ARCHIVE.open('rb') as source:
        first = source.read(8)
        size_payload, header_size = struct.unpack('<II', first)
        if size_payload != 4 or not 8 <= header_size <= min(MAX_HEADER, length - 8):
            raise ValueError('Invalid or unexpectedly large ASAR header')
        raw = source.read(header_size)
    payload_size, string_size = struct.unpack_from('<II', raw)
    if payload_size > header_size - 4 or string_size > payload_size - 4:
        raise ValueError('Invalid ASAR pickle bounds')
    encoded = raw[8:8 + string_size]
    header = json.loads(encoded)
    entries = {}

    def walk(directory, parent=''):
        for name, entry in directory['files'].items():
            if not isinstance(name, str) or name in ('.', '..') or '/' in name or '\\' in name:
                raise ValueError('Unsafe ASAR entry path')
            name = parent + name
            if 'files' in entry:
                walk(entry, name + '/')
            else:
                entries[name] = entry
    walk(header)
    return length, header_size, hashlib.sha256(encoded).hexdigest(), entries


def read_entry(name, entry, header_size, archive_size, maximum):
    if 'link' in entry:
        raise ValueError('Link metadata is not followed')
    size = entry.get('size')
    if type(size) is not int or not 0 <= size <= maximum:
        raise ValueError('Entry size is invalid or exceeds bound')
    if entry.get('unpacked'):
        target = UNPACKED / name
        if target.is_symlink() or not target.resolve().is_relative_to(UNPACKED.resolve()):
            raise ValueError('Unpacked path escapes directory or is a symlink')
        with target.open('rb') as source:
            return source.read(size)
    offset = 8 + header_size + int(entry['offset'])
    if offset < 8 + header_size or offset + size > archive_size:
        raise ValueError('Entry extends beyond ASAR boundary')
    with ARCHIVE.open('rb') as source:
        source.seek(offset)
        data = source.read(size)
    if len(data) != size:
        raise ValueError('Truncated ASAR entry')
    return data


def pe_metadata(data):
    if data[:4] == b'\x7fELF':
        return {'format': 'ELF', 'class_bits': {1: 32, 2: 64}.get(data[4]), 'machine': struct.unpack_from('<H', data, 18)[0] if len(data) > 20 else None}
    if data[:2] != b'MZ' or len(data) < 64:
        return {'format': 'unknown'}
    pe_offset = struct.unpack_from('<I', data, 60)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset+4] != b'PE\0\0':
        return {'format': 'MZ-without-valid-PE'}
    machine, sections = struct.unpack_from('<HH', data, pe_offset+4)
    optional_size = struct.unpack_from('<H', data, pe_offset+20)[0]
    optional_start = pe_offset+24
    magic = struct.unpack_from('<H', data, optional_start)[0]
    directories = optional_start + {0x10b: 96, 0x20b: 112}.get(magic, optional_size)
    section_table = optional_start + optional_size
    section_bounds = []
    for index in range(sections):
        begin = section_table + index*40
        if begin + 40 > len(data):
            break
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from('<IIII', data, begin+8)
        section_bounds.append((rva, max(virtual_size, raw_size), raw_offset, raw_size))

    def at_rva(rva):
        for start, span, raw_offset, raw_size in section_bounds:
            if start <= rva < start + span and rva-start < raw_size:
                offset = raw_offset + rva-start
                if offset < len(data):
                    return offset
        return None

    imports = []
    if directories + 16 <= optional_start + optional_size:
        import_rva, import_size = struct.unpack_from('<II', data, directories + 8)
        location = at_rva(import_rva)
        if location is not None:
            for index in range(min(import_size // 20 + 1, 1024)):
                begin = location + index*20
                if begin + 20 > len(data):
                    break
                descriptor = struct.unpack_from('<IIIII', data, begin)
                if not any(descriptor):
                    break
                name_location = at_rva(descriptor[3])
                if name_location is not None:
                    imports.append(data[name_location:name_location+256].split(b'\0', 1)[0].decode('ascii', 'replace'))
    return {'format': 'PE', 'machine': hex(machine), 'architecture': {0x14c: 'x86', 0x8664: 'x86_64', 0xaa64: 'arm64'}.get(machine, 'other'), 'imports': sorted(set(imports), key=str.lower)}


def main():
    archive_size, header_size, header_hash, entries = parse_header()
    errors = []
    packages = {}
    allowed = ('name', 'version', 'main', 'type', 'engines', 'os', 'cpu', 'dependencies', 'optionalDependencies', 'peerDependencies', 'peerDependenciesMeta', 'gypfile')
    for name, entry in sorted(entries.items()):
        if PurePosixPath(name).name != 'package.json':
            continue
        try:
            document = json.loads(read_entry(name, entry, header_size, archive_size, MAX_METADATA))
            packages[name] = {key: document[key] for key in allowed if key in document}
        except (OSError, ValueError, TypeError) as error:
            errors.append({'path': name, 'error': type(error).__name__})
    root = packages.get('package.json')
    if root is None:
        raise ValueError('Root package.json could not be read')
    binaries = []
    package_directories = sorted(((str(PurePosixPath(name).parent), name) for name in packages), key=lambda item: len(item[0]), reverse=True)
    for name, entry in sorted(entries.items()):
        if PurePosixPath(name).suffix.lower() not in ('.node', '.dll', '.exe', '.so', '.dylib'):
            continue
        owner = next((package for directory, package in package_directories if name.startswith(directory + '/')), None)
        item = {'path': name, 'bytes': entry.get('size'), 'unpacked': bool(entry.get('unpacked')), 'package': owner}
        try:
            item.update(pe_metadata(read_entry(name, entry, header_size, archive_size, MAX_BINARY)))
        except (OSError, ValueError, TypeError, struct.error) as error:
            item['metadata_error'] = type(error).__name__
        binaries.append(item)
    unpacked_inventory = []
    if UNPACKED.is_dir():
        for path in sorted(UNPACKED.rglob('*')):
            if path.is_file() and path.suffix.lower() in ('.node', '.dll', '.exe', '.so', '.dylib'):
                relative = path.relative_to(UNPACKED).as_posix()
                unpacked_inventory.append({'path': relative, 'bytes': path.stat().st_size, 'in_asar_header': relative in entries})
    owners = {item['package'] for item in binaries if item['package']}
    main_name = PurePosixPath(root.get('main', '')).as_posix()
    main_entry = entries.get(main_name)
    report = {
        'inspected_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'ASAR header, package.json metadata and native executable format/import metadata only; no app code executed, auth/lockfiles/logs or APIs accessed.',
        'archive': str(ARCHIVE), 'archive_bytes': archive_size, 'header_bytes': header_size, 'header_json_sha256': header_hash,
        'entries': len(entries), 'extensions': dict(Counter(PurePosixPath(name).suffix.lower() for name in entries)),
        'root_package': root, 'package_count': len(packages), 'packages': packages,
        'native_packages': {name: packages[name] for name in sorted(owners)},
        'platform_restricted_packages': {name: package for name, package in packages.items() if 'os' in package or 'cpu' in package},
        'binary_entries': binaries, 'unpacked_exists': UNPACKED.exists(), 'unpacked_is_directory': UNPACKED.is_dir(), 'unpacked_binary_inventory': unpacked_inventory,
        'root_main_present': main_entry is not None,
        'root_main_entry': {'path': main_name, 'bytes': main_entry.get('size'), 'unpacked': bool(main_entry.get('unpacked'))} if main_entry else None,
        'optional_dependency_declarations': {name: package['optionalDependencies'] for name, package in packages.items() if package.get('optionalDependencies')},
        'errors': errors,
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
