"""Persist exactly the two verified game bind mounts in this laboratory."""
import os
from pathlib import Path
import shutil
import subprocess

if os.getuid() != 0:
    raise SystemExit('Root required for fixed mount configuration')
volume = Path('/var/lib/lol-lab/game-data')
uuid = 'aa6311c7-ff75-4b48-b5e4-971836c18ca6'
if subprocess.check_output(['findmnt', '-n', '-o', 'UUID', '--target', str(volume)], text=True).strip() != uuid:
    raise SystemExit('Unexpected game volume')
root = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games')
lines = []
for name in ('League of Legends', 'Teamfight Tactics'):
    source, target = volume / name, root / name
    if not os.path.ismount(target) or source.stat().st_ino != target.stat().st_ino or source.stat().st_dev != target.stat().st_dev:
        raise SystemExit('Verified bind mount required')
    def field(path):
        return str(path).replace(' ', r'\040')
    lines.append(f'{field(source)} {field(target)} none bind,nofail,x-systemd.requires-mounts-for={volume} 0 0\n')
fstab = Path('/etc/fstab')
backup = Path('/etc/fstab.before-lol-binds')
if backup.exists():
    raise SystemExit('Backup already exists')
text = fstab.read_text()
if any(line.split()[1] in text for line in lines):
    raise SystemExit('Existing target mount configuration')
shutil.copy2(fstab, backup)
with fstab.open('a') as handle:
    handle.writelines(lines)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['findmnt', '--verify', '--tab-file', str(fstab)], check=True)
print('Game volume and both bind mounts persisted', flush=True)
