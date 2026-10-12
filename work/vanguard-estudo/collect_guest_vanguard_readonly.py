"""Read public Vanguard files and query SCM only; never start/stop a service."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess

import pefile

prefix = Path("/home/lab/lol-lab/prefix")
folder = prefix / "drive_c/Program Files/Riot Vanguard"
if os.geteuid() != pwd.getpwnam("lab").pw_uid:
    raise RuntimeError("This collector must run as lab")

baseline = {
    "vgk.sys": {"bytes": 109721528, "version": "1.19.1-18+20261001.143443", "sha256": "8ba32cfbc4a07fd41a082344e23e312515ffafef0e568ba72e7d33e83b558f13"},
    "vgc.exe": {"bytes": 107505544, "version": "1.19.1-18+20261001.143443", "sha256": "c8f330a77351f36e1112d0b94972a735a7747fc33a4aa4735d95f43f01637c51"},
    "vgm.exe": {"bytes": 33861928, "version": "1.19.1-18+20261001.143443", "sha256": "55e25cce83c8ec9088b99d1193a7aa750609e69ed8cfc7c758076ec3591de3d9"},
    "vgrl.dll": {"bytes": 7930376, "version": "1.19.1-18+20261001.143443", "sha256": "d76344bcda5acba14156b090e037ccc270f15d3571d2c629a83f5f7263be32c0"},
}

def utc():
    return datetime.now(timezone.utc).isoformat()

def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def decode_version(value):
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)

files = []
started = utc()
for name, reference in baseline.items():
    path = folder / name
    item = {"name": name, "path": str(path), "baseline": reference}
    try:
        stat = path.stat()
        item.update({"present": True, "bytes_first": stat.st_size, "mtime_ns_first": stat.st_mtime_ns, "sha256_first": file_hash(path), "first_collected_at_utc": utc()})
        pe = pefile.PE(str(path), fast_load=True)
        try:
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
            versions = []
            for group in getattr(pe, "FileInfo", []):
                for info in group:
                    if getattr(info, "Key", None) != b"StringFileInfo":
                        continue
                    for table in getattr(info, "StringTable", []):
                        entries = getattr(table, "entries", {})
                        versions.append({"file_version": decode_version(entries.get(b"FileVersion", entries.get("FileVersion", ""))), "product_version": decode_version(entries.get(b"ProductVersion", entries.get("ProductVersion", "")))})
            item["version_resources"] = versions
            item["machine"] = f"0x{pe.FILE_HEADER.Machine:04x}"
            item["optional_magic"] = f"0x{pe.OPTIONAL_HEADER.Magic:04x}"
            item["subsystem"] = pe.OPTIONAL_HEADER.Subsystem
            item["pe_parser_warnings"] = pe.get_warnings()
        finally:
            pe.close()
            del pe
    except FileNotFoundError:
        item["present"] = False
    except Exception as error:
        item["error"] = str(error)
    files.append(item)

environment = os.environ.copy()
environment.update({"WINEPREFIX": str(prefix), "WINEDEBUG": "-all", "DISPLAY": ":99"})
queries = []
for service in ("vgk", "vgc"):
    command = ["/usr/bin/wine", "sc.exe", "query", service]
    collected_at = utc()
    try:
        result = subprocess.run(command, env=environment, capture_output=True, text=True, errors="replace", timeout=20)
        queries.append({"service": service, "collected_at_utc": collected_at, "command": "wine sc.exe query " + service, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    except subprocess.TimeoutExpired:
        queries.append({"service": service, "collected_at_utc": collected_at, "command": "wine sc.exe query " + service, "error": "Query timed out after 20 seconds; no service start/stop command requested"})

for item in files:
    if not item.get("present"):
        continue
    path = Path(item["path"])
    try:
        stat = path.stat()
        item.update({"bytes_second": stat.st_size, "mtime_ns_second": stat.st_mtime_ns, "sha256_second": file_hash(path), "second_collected_at_utc": utc()})
        item["stable_between_two_reads"] = item["sha256_first"] == item["sha256_second"] and item["bytes_first"] == item["bytes_second"] and item["mtime_ns_first"] == item["mtime_ns_second"]
        item["matches_baseline_sha256"] = item["sha256_second"] == item["baseline"]["sha256"]
        item["matches_baseline_bytes"] = item["bytes_second"] == item["baseline"]["bytes"]
        item["matches_baseline_version"] = any(v["file_version"] == item["baseline"]["version"] for v in item.get("version_resources", []))
    except Exception as error:
        item["second_read_error"] = str(error)

print(json.dumps({"started_at_utc": started, "completed_at_utc": utc(), "uid": os.geteuid(), "user": pwd.getpwuid(os.geteuid()).pw_name, "prefix": str(prefix), "method": "Two read-only SHA256 passes and PE version-resource parsing of fixed public Vanguard file paths; only SCM query commands were requested", "files": files, "service_queries": queries, "limitations": "SCM status is reported by the Wine prefix. File presence/hash/service status does not establish execution in the Linux kernel or anticheat acceptance. No authentication data, lockfiles, client configuration or logs were read."}, indent=2, ensure_ascii=False))
