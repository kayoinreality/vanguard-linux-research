import json
import re
from pathlib import Path

import pefile

root = Path('/home/lab/lol-lab/prefix/drive_c')
result = {'binaries': [], 'technical_events': [], 'processes': []}
for path in (root / 'Riot Games').rglob('*.exe'):
    if path.name not in {'RiotClientServices.exe', 'RiotClientElectron.exe', 'Riot Client.exe', 'LeagueClient.exe', 'League of Legends.exe'}:
        continue
    pe = pefile.PE(str(path), fast_load=True)
    version = None
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    if hasattr(pe, 'VS_FIXEDFILEINFO'):
        info = pe.VS_FIXEDFILEINFO[0]
        version = '.'.join(str(x) for x in (info.FileVersionMS >> 16, info.FileVersionMS & 65535, info.FileVersionLS >> 16, info.FileVersionLS & 65535))
    result['binaries'].append({'path': str(path.relative_to(root)), 'bytes': path.stat().st_size, 'version': version})
    pe.close()

interesting = re.compile(r'error|failed|fatal|gpu|angle|exception|unsupported|dxgi|render', re.I)
sensitive = re.compile(r'auth|token|password|cookie|ticket|secret|session|player|account|user|credential|email|nonce|bearer|private|api.?key', re.I)
logs = root / 'users/lab/AppData/Local/Riot Games/Riot Client/Logs'
latest = {}
for candidate in logs.rglob('*.log'):
    if candidate.parent not in latest or candidate.stat().st_mtime > latest[candidate.parent].stat().st_mtime:
        latest[candidate.parent] = candidate
for path in latest.values():
    if path.stat().st_size > 4 * 1024 * 1024:
        continue
    events = [line[:1200] for line in path.read_text(errors='replace').splitlines() if interesting.search(line) and not sensitive.search(line)]
    if events:
        result['technical_events'].append({'file': str(path.relative_to(logs)), 'events': events[-15:]})
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        name = (proc / 'comm').read_text().strip()
        if 'riot' not in name.lower():
            continue
        args = (proc / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        flags = [arg.split('=', 1)[0] for arg in args if arg.startswith('--')]
        result['processes'].append({'pid': int(proc.name), 'name': name, 'flag_names': flags})
    except (OSError, PermissionError):
        pass
print(json.dumps(result, indent=2, ensure_ascii=False))
