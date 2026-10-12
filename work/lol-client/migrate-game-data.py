"""Copy and verify only public game files inside the owned Arch laboratory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

if os.getuid() != 1000:
    raise SystemExit('Must run as lab')
source_root = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games')
target_root = Path('/var/lib/lol-lab/game-data')
if source_root.resolve() != source_root or target_root.resolve() != target_root:
    raise SystemExit('Unexpected laboratory path')
if not os.path.ismount(target_root):
    raise SystemExit('Game volume is not mounted')
serial = subprocess.check_output(['lsblk', '-dn', '-o', 'SERIAL', subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE', '--target', str(target_root)], text=True).strip()], text=True).strip()
if serial != '60022480ef37c8273d187c3c9461ccde':
    raise SystemExit('Mounted disk identity mismatch')
for unit in ('lol-lab-client', 'lol-lab-ui-native-v2'):
    if subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0:
        raise SystemExit('Stop client services before migration')

def manifest(root):
    entries = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            entries[relative] = ['link', os.readlink(path)]
        elif stat.S_ISDIR(info.st_mode):
            entries[relative] = ['dir', stat.S_IMODE(info.st_mode)]
        elif stat.S_ISREG(info.st_mode):
            digest = hashlib.sha256()
            with path.open('rb') as handle:
                while chunk := handle.read(4 * 1024 * 1024):
                    digest.update(chunk)
            entries[relative] = ['file', info.st_size, stat.S_IMODE(info.st_mode), digest.hexdigest()]
        else:
            raise RuntimeError('Unexpected special file')
    return entries

report = {'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'disk_serial': serial, 'games': []}
for name in ('League of Legends', 'Teamfight Tactics'):
    source, target = source_root / name, target_root / name
    backup = source_root / (name + '.before-game-data')
    if not source.is_dir() or source.is_symlink() or source.resolve() != source:
        raise SystemExit('Unexpected source directory')
    if target.exists() or target.is_symlink() or backup.exists() or backup.is_symlink():
        raise SystemExit('Destination or backup already exists')
    print('Copying ' + name, flush=True)
    shutil.copytree(source, target, symlinks=True)
    print('Verifying ' + name, flush=True)
    original, copied = manifest(source), manifest(target)
    if original != copied:
        raise SystemExit('Copy verification mismatch; original retained')
    source.rename(backup)
    source.mkdir(mode=0o755)
    try:
        subprocess.run(['sudo', 'mount', '--bind', str(target), str(source)], check=True)
        if not os.path.ismount(source) or source.stat().st_ino != target.stat().st_ino or source.stat().st_dev != target.stat().st_dev:
            raise RuntimeError('Bind mount not confirmed')
    except BaseException:
        if os.path.ismount(source):
            subprocess.run(['sudo', 'umount', str(source)], check=True)
        source.rmdir()
        backup.rename(source)
        raise
    report['games'].append({'name': name, 'entries': len(original), 'file_count': sum(value[0] == 'file' for value in original.values()), 'bytes': sum(value[1] for value in original.values() if value[0] == 'file'), 'sha256_manifest': hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest(), 'verified': True, 'original_backup_retained': str(backup)})
    Path('/home/lab/lol-lab/game-data-migration.json').write_text(json.dumps(report, indent=2))
    print('Verified and switched ' + name, flush=True)
subprocess.run(['sync'], check=True)
print('Migration complete; original backups retained for reopening verification', flush=True)
