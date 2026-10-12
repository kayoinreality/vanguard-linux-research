#!/usr/bin/env bash
set -euo pipefail
test "$(id -un)" = lab
task_dir=/home/lab/lol-lab
test -f "$task_dir/prefix/drive_c/Riot Games/Riot Client/RiotClientServices.exe"
sudo systemd-run --unit=lol-lab-client --uid=lab --property=ExitType=cgroup --property=TimeoutStopSec=5s --setenv=HOME=/home/lab --setenv=DISPLAY=:99 --setenv=WINEPREFIX="$task_dir/prefix" --setenv=WINEDEBUG=-all,err+all,+service --setenv=ELECTRON_ENABLE_LOGGING=1 --setenv='ELECTRON_LOG_FILE=C:\users\lab\AppData\Local\Riot Games\normal-electron.log' /usr/bin/wine "$task_dir/prefix/drive_c/Riot Games/Riot Client/RiotClientServices.exe"
