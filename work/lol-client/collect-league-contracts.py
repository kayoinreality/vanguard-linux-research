"""Collect public PE metadata from two fixed game images without loading them."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pefile

BASE = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games/League of Legends')
TARGETS = ('LeagueClient.exe', 'LeagueClientUx.exe')


def public_stat(stat):
    return {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def import_table(pe, attribute):
    modules = []
    for descriptor in getattr(pe, attribute, []):
        modules.append({
            'module': descriptor.dll.decode('ascii', errors='replace'),
            'symbols': [
                entry.name.decode('ascii', errors='replace') if entry.name
                else f'ordinal:{entry.ordinal}'
                for entry in descriptor.imports
            ],
        })
    return modules


def inspect(name):
    path = BASE / name
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    pe = pefile.PE(data=data, fast_load=True)
    directories = [pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
                   pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT']]
    pe.parse_data_directories(directories=directories)
    ordinary = import_table(pe, 'DIRECTORY_ENTRY_IMPORT')
    delayed = import_table(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT')
    cert = pe.OPTIONAL_HEADER.DATA_DIRECTORY[
        pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_SECURITY']]
    result = {
        'name': name,
        'guest_path': str(path),
        'sha256': hashlib.sha256(data).hexdigest(),
        'bytes_read': len(data),
        'stat_before': public_stat(before),
        'stat_after': public_stat(after),
        'metadata_stable_during_read': (
            before.st_size == after.st_size == len(data)
            and before.st_mtime_ns == after.st_mtime_ns),
        'machine': pefile.MACHINE_TYPE.get(pe.FILE_HEADER.Machine,
                                         hex(pe.FILE_HEADER.Machine)),
        'format': 'PE32+' if pe.OPTIONAL_HEADER.Magic == 0x20b else 'PE32',
        'subsystem': pefile.SUBSYSTEM_TYPE.get(pe.OPTIONAL_HEADER.Subsystem,
                                             str(pe.OPTIONAL_HEADER.Subsystem)),
        'entrypoint_rva': pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        'sections': [{
            'name': section.Name.rstrip(b'\0').decode('ascii', errors='replace'),
            'virtual_size': section.Misc_VirtualSize,
            'raw_size': section.SizeOfRawData,
            'characteristics': hex(section.Characteristics),
        } for section in pe.sections],
        'ordinary_imports': ordinary,
        'delay_imports': delayed,
        'ordinary_module_count': len(ordinary),
        'ordinary_symbol_count': sum(len(item['symbols']) for item in ordinary),
        'delay_module_count': len(delayed),
        'delay_symbol_count': sum(len(item['symbols']) for item in delayed),
        'certificate_directory': {
            'file_offset': cert.VirtualAddress,
            'bytes': cert.Size,
            'present': bool(cert.VirtualAddress and cert.Size),
            'signature_validation_performed': False,
        },
        'parser_warnings': pe.get_warnings(),
    }
    pe.close()
    return result


files = []
for target in TARGETS:
    try:
        files.append(inspect(target))
    except (OSError, pefile.PEFormatError, IndexError, ValueError) as error:
        files.append({'name': target, 'error': str(error)})

print(json.dumps({
    'schema_version': 1,
    'collected_at_utc': datetime.now(timezone.utc).isoformat(),
    'method': 'Read-only pefile inspection of fixed public executable images; '
              'ordinary and delay import tables; target images not loaded or executed.',
    'parser_version': pefile.__version__,
    'scope': list(TARGETS),
    'exclusions': ['process information', 'command-line arguments', 'authentication data',
                   'logs', 'lockfiles', 'UI state', 'protected-code disassembly',
                   'runtime DLL resolution', 'runtime call tracing',
                   'signature or attestation emulation'],
    'limitations': [
        'An imported symbol does not establish an executed call, arguments or purpose.',
        'Imports loaded dynamically are not captured by these two PE directories.',
        'Dependencies of imported modules and plugins were not recursively inspected.',
        'A declared certificate table and a SHA-256 digest do not prove authenticity.',
        'Stable file metadata is a consistency check, not a filesystem snapshot guarantee.',
        'No gameplay, CEF version, server acceptance or Linux port was validated.',
    ],
    'files': files,
}, indent=2, ensure_ascii=False))
