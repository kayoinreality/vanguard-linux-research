"""Collect allowlisted lab state without reading accounts or authentication data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import pefile

prefix = Path('/home/lab/lol-lab/prefix/drive_c')
volume = Path('/var/lib/lol-lab/game-data')
result = {'observed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'kernel': os.uname().release, 'services': {}, 'storage': [], 'public_binaries': []}
for unit in ('lol-lab-client', 'lol-lab-ui-native-v2', 'archguard-lab'):
    values = subprocess.check_output(['systemctl', 'show', unit, '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID'], text=True)
    result['services'][unit] = dict(line.split('=', 1) for line in values.splitlines())
for path in (Path('/'), volume, prefix / 'Riot Games/League of Legends', prefix / 'Riot Games/Teamfight Tactics'):
    usage = shutil.disk_usage(path)
    mount = subprocess.check_output(['findmnt', '-n', '-o', 'UUID,SOURCE,TARGET', '--target', str(path)], text=True).strip()
    result['storage'].append({'path': str(path), 'total_bytes': usage.total, 'used_bytes': usage.used, 'free_bytes': usage.free, 'mount': mount})
for relative in ('Riot Games/League of Legends/LeagueClient.exe', 'Riot Games/League of Legends/LeagueClientUx.exe', 'Riot Games/League of Legends/Game/League of Legends.exe'):
    path = prefix / relative
    entry = {'path': relative, 'present': path.is_file()}
    if path.is_file():
        entry['bytes'] = path.stat().st_size
        entry['sha256'] = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        pe = pefile.PE(str(path), fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
        if hasattr(pe, 'VS_FIXEDFILEINFO'):
            info = pe.VS_FIXEDFILEINFO[0]
            entry['version'] = '.'.join(str(number) for number in (info.FileVersionMS >> 16, info.FileVersionMS & 65535, info.FileVersionLS >> 16, info.FileVersionLS & 65535))
        pe.close()
    result['public_binaries'].append(entry)
report = Path('/home/lab/lol-lab/game-data-migration.json')
if report.is_file():
    result['game_migration'] = json.loads(report.read_text())
print(json.dumps(result, indent=2))
