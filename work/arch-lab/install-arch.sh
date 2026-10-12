#!/usr/bin/env bash
# Run only in the official Arch live ISO inside the dedicated Hyper-V lab VM.
# Required environment: LAB_INSTANCE_ID and LAB_SSH_PUBLIC_KEY (Ed25519 public key).
set -Eeuo pipefail
umask 022

readonly DISK=/dev/sda
readonly EXPECTED_BYTES=53687091200
readonly TARGET=/mnt
readonly LIVE_STATE=/run/arch-lab
readonly STATE_REL=/var/lib/arch-lab
readonly LIVE_LOG="$LIVE_STATE/install.log"
state_ready=false
probe_mounted=false

[[ $EUID -eq 0 ]] || { printf 'Run as root in the Arch live VM.\n' >&2; exit 1; }
mkdir -p "$LIVE_STATE"
exec 3>&1
exec >>"$LIVE_LOG" 2>&1

log() {
    printf '[%s] %s\n' "$(date --utc +%FT%TZ)" "$*" | tee /dev/fd/3
}

fail() {
    log "ERROR: $*"
    exit 1
}

finish() {
    local rc=$?
    trap - EXIT
    if (( rc != 0 )); then
        log "Installation stopped (exit $rc). No reboot will be requested."
        printf 'failed\n' >"$LIVE_STATE/status"
        if $state_ready && mountpoint -q "$TARGET"; then
            printf 'failed\n' >"$TARGET$STATE_REL/status"
            cp -- "$LIVE_LOG" "$TARGET$STATE_REL/install.log" || true
            sync || true
        fi
    fi
    if $probe_mounted; then
        umount "$LIVE_STATE/existing" || true
    fi
    exit "$rc"
}
trap finish EXIT
trap 'log "Command failed at line $LINENO (exit $?)."' ERR

[[ ${LAB_INSTANCE_ID:-} =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] \
    || fail 'LAB_INSTANCE_ID is missing or malformed.'
readonly KEY_PATTERN='^ssh-ed25519[[:blank:]]+[A-Za-z0-9+/]+={0,2}([[:blank:]]+.*)?$'
[[ ${LAB_SSH_PUBLIC_KEY:-} =~ $KEY_PATTERN \
    && $LAB_SSH_PUBLIC_KEY != *$'\n'* && $LAB_SSH_PUBLIC_KEY != *$'\r'* ]] \
    || fail 'Provide exactly one plain Ed25519 public key.'

for command in systemd-detect-virt findmnt lsblk blockdev wipefs blkid \
    sfdisk mkfs.fat mkfs.ext4 mount umount mountpoint udevadm pacstrap \
    genfstab arch-chroot ssh-keygen getconf awk grep tee sync flock; do
    command -v "$command" >/dev/null || fail "Missing live tool: $command"
done
exec 9>"$LIVE_STATE/install.lock"
flock --nonblock 9 || fail 'An installer is already running in this live environment.'
printf '%s\n' "$LAB_SSH_PUBLIC_KEY" >"$LIVE_STATE/authorized-key.pub"
ssh-keygen -lf "$LIVE_STATE/authorized-key.pub" >/dev/null \
    || fail 'The public key could not be parsed.'

[[ $(systemd-detect-virt) == microsoft ]] || fail 'This is not a Hyper-V VM.'
[[ -d /sys/firmware/efi ]] || fail 'UEFI boot is required.'
[[ -f /etc/arch-release && -d /run/archiso ]] || fail 'The Arch live ISO is required.'
grep -Eq '(^|[[:space:]])archisobasedir=arch([[:space:]]|$)' /proc/cmdline \
    || fail 'The boot command line does not identify the official Arch live environment.'
[[ $(findmnt -nro FSTYPE /) == overlay ]] || fail 'The live overlay root is missing.'
findmnt -rn -o TARGET,FSTYPE | awk \
    '$1 ~ /^\/run\/archiso\// && $2 ~ /^(squashfs|erofs|tmpfs|overlay)$/ { found=1 } END { exit !found }' \
    || fail 'No Arch live backing mount was found.'
[[ $(getconf _NPROCESSORS_ONLN) == 4 ]] || fail 'The dedicated VM must have four virtual CPUs.'
memory_kib=$(awk '/^MemTotal:/ { print $2 }' /proc/meminfo)
(( memory_kib >= 1835008 && memory_kib <= 4194304 )) \
    || fail 'The VM memory is outside the expected 2–4 GiB allocation (allowing kernel overhead).'

mapfile -t disks < <(lsblk -dnpo NAME,TYPE | awk '$2 == "disk" { print $1 }')
[[ ${#disks[@]} -eq 1 && ${disks[0]} == "$DISK" ]] \
    || fail 'Expected exactly one virtual disk, /dev/sda; refusing ambiguous storage.'
[[ -b "$DISK" && $(cat /sys/block/sda/removable) == 0 ]] \
    || fail 'The expected disk is absent or removable.'
[[ $(blockdev --getsize64 "$DISK") == "$EXPECTED_BYTES" ]] \
    || fail 'The disk must be exactly 50 GiB (53687091200 bytes).'
[[ $(blockdev --getro "$DISK") == 0 ]] || fail 'The disk is read-only.'
[[ -z $(lsblk -nro MOUNTPOINTS "$DISK" | tr -d '[:space:]') ]] \
    || fail 'The target disk or a child device is mounted or in use as swap.'
[[ -z $(ls -A /sys/block/sda/holders) ]] || fail 'The disk has active block-device holders.'
log "Preflight confirmed Hyper-V, Arch live UEFI, one 50 GiB disk, instance $LAB_INSTANCE_ID."

# Existing disks are never formatted. Only our completed installation is accepted.
mapfile -t block_nodes < <(lsblk -nrpo NAME "$DISK")
signatures=$(wipefs --no-act --noheadings --output TYPE "$DISK")
if (( ${#block_nodes[@]} != 1 )) || [[ -n $signatures ]]; then
    [[ ${#block_nodes[@]} -eq 3 && ${block_nodes[1]} == /dev/sda1 && ${block_nodes[2]} == /dev/sda2 ]] \
        || fail 'Existing disk layout is not the owned two-partition lab layout.'
    [[ $(blkid -s PTTYPE -o value "$DISK") == gpt \
        && $(blkid -s TYPE -o value /dev/sda1) == vfat \
        && $(blkid -s LABEL -o value /dev/sda1) == ARCHLABESP \
        && $(blkid -s TYPE -o value /dev/sda2) == ext4 \
        && $(blkid -s LABEL -o value /dev/sda2) == ARCHLABROOT ]] \
        || fail 'Existing filesystem signatures do not match the lab.'
    mkdir -p "$LIVE_STATE/existing"
    mount -o ro,noload /dev/sda2 "$LIVE_STATE/existing"
    probe_mounted=true
    existing_state="$LIVE_STATE/existing$STATE_REL"
    [[ -f "$existing_state/instance-id" && ! -L "$existing_state/instance-id" \
        && -f "$existing_state/status" && ! -L "$existing_state/status" ]] \
        || fail 'No regular ownership and completion markers were found.'
    [[ $(cat "$existing_state/instance-id") == "$LAB_INSTANCE_ID" ]] \
        || fail 'The disk belongs to a different lab instance.'
    [[ $(cat "$existing_state/status") == success ]] \
        || fail 'This instance contains an incomplete installation; manual review is required.'
    [[ -f "$existing_state/install-success" && ! -L "$existing_state/install-success" \
        && $(cat "$existing_state/install-success") == "$LAB_INSTANCE_ID" ]] \
        || fail 'The host integration completion marker is absent or mismatched.'
    [[ $(realpath "$existing_state") == "$existing_state" ]] \
        || fail 'The ownership directory contains a symlink.'
    log 'This instance is already installed successfully; no installation changes are needed.'
    umount "$LIVE_STATE/existing"
    probe_mounted=false
    mount /dev/sda2 "$LIVE_STATE/existing"
    probe_mounted=true
    cat "$LIVE_LOG" >>"$existing_state/install.log"
    printf 'success\n' >"$LIVE_STATE/status"
    sync
    umount "$LIVE_STATE/existing"
    probe_mounted=false
    exit 0
fi

# Probe both partition metadata and filesystem signatures before the first write.
if blkid -p "$DISK" >"$LIVE_STATE/disk-probe.txt" 2>&1; then
    fail 'A filesystem or partition signature already exists.'
else
    probe_rc=$?
    [[ $probe_rc -eq 2 ]] || fail "The blank-disk probe failed unexpectedly (exit $probe_rc)."
fi
[[ -z $(sfdisk --list "$DISK" 2>/dev/null | awk '/^\/dev\/sda[0-9]+/ { print }') ]] \
    || fail 'A partition is already present.'
mkdir -p "$TARGET"
! mountpoint -q "$TARGET" || fail '/mnt is already a mountpoint.'
[[ -z $(ls -A "$TARGET") ]] || fail '/mnt is not empty.'

log 'Creating GPT, a 1 GiB EFI partition, and the ext4 root on the verified empty virtual disk.'
sfdisk --lock "$DISK" <<'PARTITIONS'
label: gpt
start=1MiB, size=1GiB, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B, name="Arch Lab EFI"
type=0FC63DAF-8483-4772-8E79-3D69D8477DE4, name="Arch Lab Root"
PARTITIONS
udevadm settle
[[ -b /dev/sda1 && -b /dev/sda2 ]] || fail 'The new partitions did not appear.'
mkfs.fat -F 32 -n ARCHLABESP /dev/sda1
mkfs.ext4 -L ARCHLABROOT /dev/sda2
mount /dev/sda2 "$TARGET"
mkdir -p "$TARGET/boot" "$TARGET$STATE_REL"
mount /dev/sda1 "$TARGET/boot"
printf '%s\n' "$LAB_INSTANCE_ID" >"$TARGET$STATE_REL/instance-id"
printf 'installing\n' >"$TARGET$STATE_REL/status"
state_ready=true
cp -- "$LIVE_STATE/authorized-key.pub" "$TARGET$STATE_REL/authorized-key.pub"
cp -- "$LIVE_LOG" "$TARGET$STATE_REL/install.log"
sync

log 'Installing the base system, integration services, compilers, and static analysis tools.'
pacstrap -K "$TARGET" base linux openssh hyperv base-devel git rust python \
    python-pefile radare2 gdb strace
genfstab -U "$TARGET" >"$TARGET/etc/fstab"
ln -sf /usr/share/zoneinfo/America/Sao_Paulo "$TARGET/etc/localtime"
printf 'en_US.UTF-8 UTF-8\npt_BR.UTF-8 UTF-8\n' >"$TARGET/etc/locale.gen"
printf 'LANG=en_US.UTF-8\n' >"$TARGET/etc/locale.conf"
printf 'arch-lab\n' >"$TARGET/etc/hostname"
tr -d '-' </proc/sys/kernel/random/uuid >"$TARGET/etc/machine-id"

mkdir -p "$TARGET/etc/systemd/network"
cat >"$TARGET/etc/systemd/network/20-arch-lab.network" <<'NETWORK'
[Match]
Name=eth* en*

[Network]
DHCP=yes
IPv6AcceptRA=yes
NETWORK
ln -sf /run/systemd/resolve/stub-resolv.conf "$TARGET/etc/resolv.conf"

arch-chroot "$TARGET" locale-gen
arch-chroot "$TARGET" useradd --create-home --groups wheel --shell /bin/bash lab
# Disable usable passwords without the account-wide lock that can reject SSH keys.
# sshd(8) explicitly recommends *NP* for public-key-only accounts.
arch-chroot "$TARGET" usermod --password '*NP*' lab
arch-chroot "$TARGET" passwd --lock root
install -d -m 700 "$TARGET/home/lab/.ssh"
install -m 600 "$LIVE_STATE/authorized-key.pub" "$TARGET/home/lab/.ssh/authorized_keys"
arch-chroot "$TARGET" chown -R lab:lab /home/lab/.ssh
mkdir -p "$TARGET/etc/sudoers.d"
printf 'lab ALL=(ALL:ALL) NOPASSWD: ALL\n' >"$TARGET/etc/sudoers.d/10-arch-lab"
chmod 440 "$TARGET/etc/sudoers.d/10-arch-lab"
arch-chroot "$TARGET" visudo -c
cat >"$TARGET/etc/ssh/sshd_config" <<'SSH_CONFIG'
Port 22
PermitRootLogin no
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
UsePAM yes
AllowUsers lab
AuthorizedKeysFile .ssh/authorized_keys
StrictModes yes
X11Forwarding no
Subsystem sftp /usr/lib/ssh/sftp-server
SSH_CONFIG
arch-chroot "$TARGET" ssh-keygen -A
arch-chroot "$TARGET" sshd -t
arch-chroot "$TARGET" systemctl enable systemd-networkd.service systemd-resolved.service \
    sshd.service hv_kvp_daemon.service hv_vss_daemon.service

log 'Configuring Hyper-V storage drivers and the UEFI boot entry.'
mkdir -p "$TARGET/etc/mkinitcpio.conf.d"
printf 'MODULES=(hv_vmbus hv_storvsc hv_netvsc)\n' \
    >"$TARGET/etc/mkinitcpio.conf.d/arch-lab.conf"
arch-chroot "$TARGET" mkinitcpio -P
arch-chroot "$TARGET" bootctl --esp-path=/boot install
root_uuid=$(blkid -s UUID -o value /dev/sda2)
[[ $root_uuid =~ ^[a-fA-F0-9-]{36}$ ]] || fail 'The installed root UUID is malformed.'
mkdir -p "$TARGET/boot/loader/entries"
printf 'default arch-lab.conf\ntimeout 2\neditor no\n' >"$TARGET/boot/loader/loader.conf"
cat >"$TARGET/boot/loader/entries/arch-lab.conf" <<BOOT_ENTRY
title Arch Linux Laboratory
linux /vmlinuz-linux
initrd /initramfs-linux.img
options root=UUID=$root_uuid rw
BOOT_ENTRY

# Intentionally saved for execution after boot over SSH as the ordinary lab user.
mkdir -p "$TARGET/usr/local/bin"
cat >"$TARGET/usr/local/bin/arch-lab-validate" <<'SMOKE_CHECK'
#!/usr/bin/env bash
set -Eeuo pipefail
[[ $(systemd-detect-virt) == microsoft ]] || { printf 'Expected the Hyper-V lab.\n' >&2; exit 1; }
[[ $(id -un) == lab ]] || { printf 'Run the validation as the lab user.\n' >&2; exit 1; }
[[ $(cat /var/lib/arch-lab/status) == success ]] || { printf 'Installation is incomplete.\n' >&2; exit 1; }
for service in sshd.service systemd-networkd.service systemd-resolved.service; do
    systemctl is-active --quiet "$service"
done
sudo -n true
scratch=$(mktemp -d /tmp/arch-lab-smoke.XXXXXXXX)
trap 'rm -rf -- "$scratch"' EXIT
printf '#include <stdio.h>\nint main(void) { puts("C compiler: OK"); return 0; }\n' >"$scratch/check.c"
gcc -Wall -Wextra -Werror "$scratch/check.c" -o "$scratch/check-c"
"$scratch/check-c"
printf 'fn main() { println!("Rust compiler: OK"); }\n' >"$scratch/check.rs"
rustc -D warnings "$scratch/check.rs" -o "$scratch/check-rust"
"$scratch/check-rust"
python -c 'import pefile; print("Python and PE parser: OK")'
cargo --version
radare2 -v
gdb --version
strace -V
printf 'success\n' | sudo -n tee /var/lib/arch-lab/validation-status >/dev/null
date --utc +%FT%TZ | sudo -n tee /var/lib/arch-lab/validated-at >/dev/null
printf 'Own-program smoke checks passed.\n'
SMOKE_CHECK
chmod 755 "$TARGET/usr/local/bin/arch-lab-validate"
arch-chroot "$TARGET" pacman -Q >"$TARGET$STATE_REL/packages.txt"
printf 'pending-post-boot\n' >"$TARGET$STATE_REL/validation-status"
ssh-keygen -lf "$TARGET/etc/ssh/ssh_host_ed25519_key.pub" \
    >"$TARGET$STATE_REL/ssh-host-fingerprint.txt"
[[ -s "$TARGET/boot/vmlinuz-linux" && -s "$TARGET/boot/initramfs-linux.img" \
    && -s "$TARGET/boot/EFI/BOOT/BOOTX64.EFI" ]] || fail 'Required boot files are missing.'

log 'Installation configured successfully. Post-boot SSH and compiler checks are pending.'
printf '%s\n' "$(date --utc +%FT%TZ)" >"$TARGET$STATE_REL/installed-at"
cp -- "$LIVE_LOG" "$TARGET$STATE_REL/install.log"
printf 'success\n' >"$TARGET$STATE_REL/status"
printf '%s' "$LAB_INSTANCE_ID" >"$TARGET$STATE_REL/install-success"
printf 'success\n' >"$LIVE_STATE/status"
sync
# pacstrap can leave its keyring agent outside the chroot, holding the target.
# Only terminate agents whose explicit homedir is this new installation's keyring.
for lab_proc_dir in /proc/[0-9]*; do
    [[ -r "$lab_proc_dir/comm" && $(cat "$lab_proc_dir/comm") == gpg-agent ]] || continue
    mapfile -d '' -t lab_proc_args <"$lab_proc_dir/cmdline" || continue
    for ((lab_arg=0; lab_arg+1<${#lab_proc_args[@]}; lab_arg++)); do
        if [[ ${lab_proc_args[lab_arg]} == --homedir \
            && ( ${lab_proc_args[lab_arg+1]} == "$TARGET/etc/pacman.d/gnupg" \
                || ${lab_proc_args[lab_arg+1]} == "$TARGET//etc/pacman.d/gnupg" ) ]]; then
            kill -TERM "${lab_proc_dir##*/}" || true
        fi
    done
done
sleep 1
umount -R "$TARGET"
state_ready=false
log 'Persistent success status is written. Requesting reboot into the installed virtual disk.'
systemctl reboot --no-block
