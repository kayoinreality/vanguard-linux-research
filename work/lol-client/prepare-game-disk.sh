#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" = 0
task_device=/dev/disk/by-id/scsi-360022480ef37c8273d187c3c9461ccde
task_mount=/var/lib/lol-lab/game-data
test -b "$task_device"
test "$(lsblk -dn -o SERIAL "$task_device")" = 60022480ef37c8273d187c3c9461ccde
test "$(blockdev --getsize64 "$task_device")" = 64424509440
test "$(lsblk -nr -o NAME "$task_device" | wc -l)" = 1
test "$(readlink -f "$task_device")" != "$(findmnt -n -o SOURCE /)"
if findmnt -rn -S "$task_device" >/dev/null; then echo 'New disk already mounted'; exit 1; fi
test "$(wipefs -n --json "$task_device" | python -c 'import json,sys; print(len(json.load(sys.stdin).get("signatures", [])))')" = 0
test ! -e "$task_mount"
mkfs.ext4 -L LOLLABDATA -m 1 "$task_device"
install -d -m 0755 -o root -g root /var/lib/lol-lab
install -d -m 0700 -o root -g root "$task_mount"
test "$(readlink -f "$task_mount")" = "$task_mount"
mount -o nodev,nosuid "$task_device" "$task_mount"
chown lab:lab "$task_mount"
chmod 0755 "$task_mount"
task_uuid=$(blkid -s UUID -o value "$task_device")
test -n "$task_uuid"
test ! -e /etc/fstab.before-lol-data
cp -a /etc/fstab /etc/fstab.before-lol-data
printf 'UUID=%s %s ext4 defaults,nodev,nosuid,nofail,x-systemd.device-timeout=10s 0 2\n' "$task_uuid" "$task_mount" >> /etc/fstab
systemctl daemon-reload
findmnt --verify --tab-file /etc/fstab
printf 'LAB_GAME_DATA_UUID=%s\n' "$task_uuid"
df -h "$task_mount"
