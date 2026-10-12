#!/usr/bin/env bash
set -euo pipefail
test "$(id -un)" = lab
task_dir=/home/lab/lol-lab
mkdir -p "$task_dir"
cd "$task_dir"
printf '%s  %s\n' f848d40438d9e52819aa890b382aadd43b49f86151a2ad320cc0befd265841bc LeagueInstaller-BR.exe | sha256sum -c -
python -m venv "$task_dir/web-venv"
"$task_dir/web-venv/bin/python" -m pip install websockify
git -C "$task_dir/noVNC" rev-parse HEAD > "$task_dir/novnc-commit.txt"
sudo systemd-run --unit=lol-lab-display --uid=lab --property=Restart=on-failure /usr/bin/Xvfb :99 -screen 0 1280x800x24 -nolisten tcp
for attempt in {1..20}; do
  if DISPLAY=:99 xdpyinfo >/dev/null 2>&1; then break; fi
  sleep 0.25
done
DISPLAY=:99 xdpyinfo >/dev/null
sudo systemd-run --unit=lol-lab-window-manager --uid=lab --setenv=HOME=/home/lab --setenv=DISPLAY=:99 /usr/bin/openbox
sudo systemd-run --unit=lol-lab-vnc --uid=lab /usr/bin/x11vnc -display :99 -localhost -rfbport 5901 -nopw -forever -shared
sudo systemd-run --unit=lol-lab-web --uid=lab "$task_dir/web-venv/bin/websockify" --web "$task_dir/noVNC" 127.0.0.1:6081 127.0.0.1:5901
sudo systemd-run --unit=lol-lab-installer --uid=lab --property=ExitType=cgroup --setenv=HOME=/home/lab --setenv=DISPLAY=:99 --setenv=WINEPREFIX="$task_dir/prefix" --setenv=WINEARCH=win64 /usr/bin/wine "$task_dir/LeagueInstaller-BR.exe"
wine --version
systemctl is-active lol-lab-display lol-lab-window-manager lol-lab-vnc lol-lab-web
