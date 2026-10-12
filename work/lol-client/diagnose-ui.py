"""Restart only this lab's official Electron UI with diagnostic flags.

The local backend connection arguments remain in memory and are never printed
or saved by this script. The Riot executables are not modified.
"""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

mode = sys.argv[1]
if mode not in {'gpu', 'sandbox'} or os.getuid() != 1000:
    raise SystemExit('Invalid lab invocation')
prefix = '/home/lab/lol-lab/prefix'
captured = None
deadline = time.monotonic() + 30
while time.monotonic() < deadline and captured is None:
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = (proc / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
            if not args or 'RiotClientElectron' not in args[0] or any(a.startswith('--type=') for a in args):
                continue
            env = (proc / 'environ').read_bytes().split(b'\0')
            if ('WINEPREFIX=' + prefix).encode() not in env:
                continue
            if b'lol-lab-client.service' not in (proc / 'cgroup').read_bytes():
                continue
            captured = (int(proc.name), args)
            break
        except (OSError, UnicodeError):
            continue
    if captured is None:
        time.sleep(0.1)
if captured is None:
    raise SystemExit('Lab UI process not observed')
pid, args = captured
# Keep the original UI's job object alive while testing its replacement.
# Terminating the original UI closed the backend's connection in earlier runs.
os.kill(pid, signal.SIGSTOP)
args = [a for a in args[1:] if not a.startswith('--enable-hardware-acceleration')]
# The backend can reopen its local connection after its original UI exits.
# Use only the lab instance's current local connection, without logging it.
lock = Path(prefix + '/drive_c/users/lab/AppData/Local/Riot Games/Riot Client/Config/lockfile')
time.sleep(0.2)
parts = lock.read_text().strip().split(':')
if len(parts) != 5 or not parts[0].startswith('Riot') or not parts[1].isdigit() or not parts[2].isdigit() or parts[4] not in {'http', 'https'}:
    raise SystemExit('Unexpected lab backend lockfile')
port = int(parts[2])
if not 1 <= port <= 65535:
    raise SystemExit('Invalid lab backend port')
with socket.create_connection(('127.0.0.1', port), timeout=5):
    pass
args = [a for a in args if not a.startswith(('--app-port=', '--remoting-auth-token=', '--app-pid='))]
args.extend(['--app-port=' + parts[2], '--remoting-auth-token=' + parts[3], '--app-pid=' + parts[1]])
args.extend(['--disable-gpu', '--enable-logging=file', '--log-file=C:\\users\\lab\\AppData\\Local\\Riot Games\\ui-' + mode + '.log'])
if mode == 'sandbox':
    args.append('--no-sandbox')
executable = prefix + '/drive_c/Riot Games/Riot Client/RiotClientElectron/Riot Client.exe'
env = dict(os.environ, HOME='/home/lab', DISPLAY=':99', WINEPREFIX=prefix, WINEDEBUG='-all,err+all')
log_path = Path('/home/lab/lol-lab/ui-' + mode + '-wine.log')
fd = os.open(log_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as log:
    child = subprocess.Popen(['/usr/bin/wine', executable, *args], env=env, stdout=log, stderr=log)
    print('Official lab UI launched; mode=' + mode + '; pid=' + str(child.pid), flush=True)
    try:
        code = child.wait()
    finally:
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
    raise SystemExit(code)
