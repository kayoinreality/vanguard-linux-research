"""Set the lab client's own graphics preference, preserving a local backup."""
import os
from pathlib import Path
import re

path = Path('/home/lab/lol-lab/prefix/drive_c/users/lab/AppData/Local/Riot Games/Riot Client/Config/RiotClientSettings.yaml')
if os.getuid() != 1000 or not path.is_file() or path.stat().st_size > 8192:
    raise SystemExit('Unexpected lab settings file')
original = path.read_bytes()
text = original.decode('utf-8')
newline = '\r\n' if '\r\n' in text else '\n'
if not text.startswith('install:' + newline):
    raise SystemExit('Expected install settings mapping')
backup = path.with_name('RiotClientSettings.before-software-rendering.yaml')
if not backup.exists():
    fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(original)
match = re.search(r'(?m)^([ \t]+)[\w-]+:', text)
if not match or '\t' in match.group(1):
    raise SystemExit('Unsupported YAML indentation')
indent = match.group(1)
if re.search(r'(?m)^' + re.escape(indent) + r'hardware-acceleration:', text):
    text = re.sub(r'(?m)^' + re.escape(indent) + r'hardware-acceleration:[^\r\n]*', indent + 'hardware-acceleration: false', text)
else:
    text = text.replace('install:' + newline, 'install:' + newline + indent + 'hardware-acceleration: false' + newline, 1)
path.write_bytes(text.encode('utf-8'))
print('Lab graphics preference set to software rendering; local backup retained.')
