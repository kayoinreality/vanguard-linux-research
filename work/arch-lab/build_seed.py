import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import uuid

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "vendor"))
import pycdlib

output = root.parent.parent / "outputs" / "arch-lab"
output.mkdir(parents=True, exist_ok=True)
config_path = output / "config.json"
if config_path.exists():
    instance = json.loads(config_path.read_text(encoding="utf-8"))["InstanceId"]
else:
    instance = "arch-lab-" + str(uuid.uuid4())
key_file = root / "keys" / "arch-lab-ed25519"
public_key = key_file.with_suffix(".pub").read_text(encoding="utf-8").strip()
if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: [\w-]+)?", public_key):
    raise ValueError("Unexpected SSH public key format")
installer = (root / "install-arch.sh").read_bytes().replace(b"\r\n", b"\n")
installer_b64 = base64.b64encode(installer).decode("ascii")
command = [
    "/usr/bin/env", f"LAB_INSTANCE_ID={instance}",
    f"LAB_SSH_PUBLIC_KEY={public_key}", "/usr/bin/bash", "/root/install-arch-lab.sh",
]
user_data = (
    "#cloud-config\n"
    "ssh_pwauth: false\n"
    "disable_root: true\n"
    "write_files:\n"
    "  - path: /root/install-arch-lab.sh\n"
    "    owner: root:root\n"
    "    permissions: '0700'\n"
    "    encoding: b64\n"
    f"    content: {installer_b64}\n"
    "runcmd:\n"
    f"  - {json.dumps(command)}\n"
)
contents = {
    "user-data": user_data.encode("utf-8"),
    "meta-data": f"instance-id: {instance}\nlocal-hostname: arch-lab-live\n".encode("ascii"),
    "network-config": b"version: 2\nconfig: disabled\n",
}
iso_names = {"user-data": "/USERDATA.;1", "meta-data": "/METADATA.;1", "network-config": "/NETCFG.;1"}
seed_path = root / "media" / "arch-lab-cidata.iso"
seed = pycdlib.PyCdlib()
seed.new(interchange_level=3, vol_ident="CIDATA", joliet=3, rock_ridge="1.09")
buffers = []
for name, data in contents.items():
    buffer = io.BytesIO(data)
    buffers.append(buffer)
    seed.add_fp(buffer, len(data), iso_path=iso_names[name], rr_name=name, joliet_path="/" + name)
seed.write(str(seed_path))
seed.close()
check = pycdlib.PyCdlib()
check.open(str(seed_path))
assert check.pvd.volume_identifier.decode("ascii").strip() == "CIDATA"
for name, data in contents.items():
    buffer = io.BytesIO()
    check.get_file_from_iso_fp(buffer, rr_path="/" + name)
    assert buffer.getvalue() == data, name
check.close()
arch_path = root / "media" / "archlinux-2026.10.01-x86_64.iso"
arch_hash = hashlib.file_digest(arch_path.open("rb"), "sha256").hexdigest()
expected_hash = "684ded26c63240ff4a41e8c25ee84ea6da233f557364821f13d12c2b0a9059a5"
assert arch_hash == expected_hash
config = {
    "VMName": "Arch-Lab-Vanguard", "InstanceId": instance,
    "CPUCount": 4, "StartupRAMGiB": 2, "MaximumRAMGiB": 4, "DiskGiB": 50,
    "ArchISO": {"Path": str(arch_path), "SHA256": arch_hash},
    "SeedISO": {"Path": str(seed_path), "SHA256": hashlib.file_digest(seed_path.open("rb"), "sha256").hexdigest()},
    "SSHKey": str(key_file), "SSHUser": "lab",
    "ISORelease": "2026.10.01",
    "ISOOrigin": "https://archlinux.c3sl.ufpr.br/iso/2026.10.01/archlinux-2026.10.01-x86_64.iso",
    "ReleasePage": "https://archlinux.org/releng/releases/2026.10.01/",
    "PGPVerification": {
        "Status": "valid", "Fingerprint": "3E80CA1A8B89F69CBA57D98A76A5EF9054449A5C",
        "KeySource": "WKD for pierre@archlinux.org", "Verifier": "GnuPG bundled with Git for Windows",
    },
    "InstallerSHA256": hashlib.sha256(installer).hexdigest(),
}
config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
print(json.dumps({"seed": str(seed_path), "config": str(config_path), "instance": instance, "seed_verified": True}))
