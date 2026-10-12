#!/usr/bin/env bash
set -euo pipefail
test "$(id -un)" = lab
task_dir=/home/lab/lol-lab
test -f "$task_dir/start-native-ui.py"
test -f "$task_dir/prefix/drive_c/Riot Games/Riot Client/RiotClientServices.exe"
if test -f "$task_dir/game-data-migration.json"; then
    task_volume=/var/lib/lol-lab/game-data
    mountpoint -q "$task_volume"
    test "$(findmnt -n -o UUID --target "$task_volume")" = aa6311c7-ff75-4b48-b5e4-971836c18ca6
    for task_game in 'League of Legends' 'Teamfight Tactics'; do
        task_game_path="$task_dir/prefix/drive_c/Riot Games/$task_game"
        mountpoint -q "$task_game_path"
        test "$(stat -c '%d:%i' "$task_game_path")" = "$(stat -c '%d:%i' "$task_volume/$task_game")"
    done
fi
if systemctl is-active --quiet lol-lab-ui-native-v2 && systemctl is-active --quiet lol-lab-client; then
    printf '%s\n' 'Native lab interface and backend are already running.'
    exit 0
fi
for task_swap in /var/lib/lol-lab/swapfile /var/lib/lol-lab/swapfile-extra; do
    test -f "$task_swap"
    test "$(readlink -f "$task_swap")" = "$task_swap"
    if ! sudo swapon --show=NAME --noheadings | grep -Fxq "$task_swap"; then
        sudo swapon "$task_swap"
    fi
done
lab_start() {
    local task_unit=$1
    shift
    if ! systemctl is-active --quiet "$task_unit"; then
        sudo systemctl reset-failed "$task_unit" 2>/dev/null || true
        sudo systemd-run --unit="$task_unit" --uid=lab --property=TimeoutStopSec=5s "$@"
    fi
}
lab_start lol-lab-display /usr/bin/Xvfb :99 -screen 0 1280x800x24 -nolisten tcp
for attempt in {1..20}; do
    if DISPLAY=:99 xdpyinfo >/dev/null 2>&1; then break; fi
    sleep 0.25
done
DISPLAY=:99 xdpyinfo >/dev/null
lab_start lol-lab-window-manager /usr/bin/env HOME=/home/lab DISPLAY=:99 /usr/bin/openbox
lab_start lol-lab-vnc /usr/bin/x11vnc -display :99 -localhost -rfbport 5901 -nopw -forever -shared
lab_start lol-lab-web "$task_dir/web-venv/bin/websockify" --web "$task_dir/noVNC" 127.0.0.1:6081 127.0.0.1:5901
sudo systemctl stop lol-lab-client 2>/dev/null || true
sudo systemctl reset-failed lol-lab-ui-native-v2 2>/dev/null || true
sudo systemd-run --unit=lol-lab-ui-native-v2 --uid=lab --property=ExitType=cgroup --property=TimeoutStopSec=5s /usr/bin/python "$task_dir/start-native-ui.py"
bash "$task_dir/start-client.sh"
