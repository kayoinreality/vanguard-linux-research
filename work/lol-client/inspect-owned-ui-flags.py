"""List only public argument names of the original owned UI; no values."""
import json
import os
from pathlib import Path

prefix = b'WINEPREFIX=/home/lab/lol-lab/prefix'
found = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != os.getuid():
            continue
        args = (proc / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
        if not args or 'RiotClientElectron' not in args[0] or any(arg.startswith('--type=') for arg in args):
            continue
        if prefix not in (proc / 'environ').read_bytes().split(b'\0') or b'lol-lab-client.service' not in (proc / 'cgroup').read_bytes():
            continue
        found.append({'pid': int(proc.name), 'flag_names': [arg.split('=', 1)[0] for arg in args[1:] if arg.startswith('--')]})
    except (OSError, UnicodeError):
        pass
print(json.dumps(found, indent=2))
