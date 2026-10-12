#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run this installer with sudo in the dedicated Arch VM.' >&2; exit 1; }
[[ $(systemd-detect-virt) == microsoft && -f /etc/arch-release ]] || { echo 'Expected our Arch Hyper-V lab.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
getent passwd archguard-lab >/dev/null || useradd --system --user-group --no-create-home --shell /usr/bin/nologin archguard-lab
usermod --append --groups archguard-lab lab
install -d -o root -g root -m 0755 /opt/archguard-lab /etc/archguard-lab /var/lib/archguard-lab
install -o root -g root -m 0755 "$source_dir/archguard.py" /opt/archguard-lab/archguard.py
install -o root -g root -m 0644 "$source_dir/archguard-lab.service" /etc/systemd/system/archguard-lab.service
# Enrollment is explicit and happens only on the first installation.
# Restart or reinstallation never replaces a trusted reference with changed data.
if [[ ! -e /etc/archguard-lab/manifest.json ]]; then
    [[ ! -e /var/lib/archguard-lab/demo.bin && ! -L /var/lib/archguard-lab/demo.bin ]] || { echo 'Unenrolled data already exists; review it before creating a baseline.' >&2; exit 1; }
    printf 'ArchGuard original lab fixture v1\n' > /var/lib/archguard-lab/demo.bin
    chmod 0644 /var/lib/archguard-lab/demo.bin
    python - <<'PY'
import hashlib, json
from pathlib import Path
fixture = Path('/var/lib/archguard-lab/demo.bin')
manifest = {'version': 1, 'files': [{'name': fixture.name, 'sha256': hashlib.sha256(fixture.read_bytes()).hexdigest()}]}
Path('/etc/archguard-lab/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
    chmod 0644 /etc/archguard-lab/manifest.json
fi
systemd-analyze verify /etc/systemd/system/archguard-lab.service
systemctl daemon-reload
systemctl enable archguard-lab.service
systemctl restart archguard-lab.service
for _ in {1..30}; do
    if python /opt/archguard-lab/archguard.py ping; then
        systemctl is-active --quiet archguard-lab.service
        exit 0
    fi
    sleep 0.2
done
echo 'The service did not become ready.' >&2
exit 1
