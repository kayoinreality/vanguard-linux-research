"""Release verified duplicate public game files after the migration is checked."""
import json
import os
from pathlib import Path
import shutil
import subprocess

if os.getuid() != 1000:
    raise SystemExit('Must run as lab')
root = Path('/home/lab/lol-lab/prefix/drive_c/Riot Games')
volume = Path('/var/lib/lol-lab/game-data')
if root.resolve() != root or volume.resolve() != volume:
    raise SystemExit('Unexpected laboratory path')
if subprocess.check_output(['findmnt', '-n', '-o', 'UUID', '--target', str(volume)], text=True).strip() != 'aa6311c7-ff75-4b48-b5e4-971836c18ca6':
    raise SystemExit('Unexpected game volume')
if subprocess.run(['systemctl', 'is-active', '--quiet', 'lol-lab-client']).returncode != 0:
    raise SystemExit('Client must have reopened successfully first')
report_path = Path('/home/lab/lol-lab/game-data-migration.json')
report = json.loads(report_path.read_text())
names = ('League of Legends', 'Teamfight Tactics')
if tuple(game['name'] for game in report['games']) != names or not all(game['verified'] for game in report['games']):
    raise SystemExit('Both games must have passed copy verification')
for name in names:
    mount, target = root / name, volume / name
    backup = root / (name + '.before-game-data')
    if not os.path.ismount(mount) or mount.stat().st_dev != target.stat().st_dev or mount.stat().st_ino != target.stat().st_ino:
        raise SystemExit('Game bind mount mismatch')
    if backup.is_symlink() or backup.resolve() != backup or backup.parent != root or not backup.is_dir() or backup.stat().st_dev != root.stat().st_dev or os.path.ismount(backup):
        raise SystemExit('Backup path is not the owned original directory')
for game in report['games']:
    backup = root / (game['name'] + '.before-game-data')
    shutil.rmtree(backup)
    game['duplicate_released_after_mount_and_client_verification'] = True
report_path.write_text(json.dumps(report, indent=2))
subprocess.run(['sync'], check=True)
print('Verified original duplicates released; game files remain on new volume')
