#!/usr/bin/env bash
set -euo pipefail
test "$(id -un)" = lab
task_dir=/home/lab/lol-lab
task_exe="$task_dir/prefix/drive_c/Riot Games/Riot Client/RiotClientServices.exe"
test -f "$task_exe"
systemctl is-active --quiet lol-lab-client.service
umask 077
export HOME=/home/lab DISPLAY=:99 WINEPREFIX="$task_dir/prefix" WINEDEBUG=-all
wine "$task_exe" --launch-product=league_of_legends --launch-patchline=live > "$task_dir/launch-request.log" 2>&1
printf '%s\n' 'Official product launch request finished.'
