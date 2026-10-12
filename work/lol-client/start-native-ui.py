"""Try the lab's unchanged Riot ASAR with Linux Electron.

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

mode = 'native'
if os.getuid() != 1000:
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
args = [a for a in args[1:] if not a.startswith(('--enable-hardware-acceleration', '--log-dir=', '--user-data-root=', '--app-root='))]
port_arg = next((a.partition('=')[2] for a in args if a.startswith('--app-port=')), '')
if not port_arg.isdigit():
    raise SystemExit('Original UI backend port unavailable')
port = int(port_arg)
if not 1 <= port <= 65535:
    raise SystemExit('Invalid lab backend port')
ready = False
deadline = time.monotonic() + 8
while time.monotonic() < deadline:
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5):
            ready = True
            break
    except OSError:
        time.sleep(0.1)
print('Local backend socket ready=' + str(ready), flush=True)
args = [a for a in args if not a.startswith('--app-pid=')]
backend_pid = subprocess.check_output(['systemctl', 'show', 'lol-lab-client', '--property=MainPID', '--value'], text=True).strip()
if not backend_pid.isdigit() or int(backend_pid) < 2:
    raise SystemExit('Lab backend process unavailable')
args.append('--app-pid=' + backend_pid)
logs = Path('/home/lab/lol-lab/native-logs')
logs.mkdir(exist_ok=True, mode=0o700)
args.extend(['--disable-gpu', '--enable-logging=file', '--log-file=/home/lab/lol-lab/native-electron.log', '--log-dir=' + str(logs), '--user-data-root=' + prefix + '/drive_c/users/lab/AppData/Local/Riot Games/Riot Client', '--app-root=' + prefix + '/drive_c/Riot Games/Riot Client'])
executable = prefix + '/drive_c/Riot Games/Riot Client/RiotClientElectron/resources/app.asar'
env = dict(os.environ, HOME='/home/lab', DISPLAY=':99', XDG_CONFIG_HOME='/home/lab/lol-lab/native-user')
for key in ('ELECTRON_LOG_FILE', 'ELECTRON_ENABLE_LOGGING', 'WINEPREFIX', 'WINEDEBUG'):
    env.pop(key, None)
log_path = Path('/home/lab/lol-lab/ui-native.log')
fd = os.open(log_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as log:
    os.kill(pid, signal.SIGSTOP)
    try:
        child = subprocess.Popen(['/usr/bin/electron44', executable, *args], env=env, stdout=log, stderr=log)
        print('Original Riot package launched with Linux Electron; pid=' + str(child.pid), flush=True)
        code = child.wait()
    finally:
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
    raise SystemExit(code)
