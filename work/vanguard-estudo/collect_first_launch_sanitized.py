"""Read-only launch inventory. Output only fixed names, numbers and categories."""
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pwd
import re

import pefile

if os.geteuid() != pwd.getpwnam("lab").pw_uid:
    raise RuntimeError("Wrong collector UID")

prefix = Path("/home/lab/lol-lab/prefix")
riot_root = prefix / "drive_c/Riot Games"
known_exes = {
    "LeagueClient.exe", "LeagueClientUx.exe", "LeagueClientUxRender.exe",
    "League of Legends.exe", "LeagueCrashHandler64.exe",
    "LeagueClientCrashHandler.exe", "LeagueClientUxCrashHandler.exe",
    "RiotClientServices.exe", "RiotClientUx.exe", "RiotClientUxRender.exe",
    "RiotClientCrashHandler.exe",
}
required = {
    "league_client": riot_root / "League of Legends/LeagueClient.exe",
    "league_game": riot_root / "League of Legends/Game/League of Legends.exe",
    "riot_services": riot_root / "Riot Client/RiotClientServices.exe",
}

def utc(value=None):
    return datetime.now(timezone.utc).isoformat() if value is None else datetime.fromtimestamp(value, timezone.utc).isoformat()

started = utc()
exe_metadata = []
discovered = {}
scan_errors = 0
for application_root in (riot_root / "League of Legends", riot_root / "Riot Client"):
    if not application_root.is_dir():
        continue
    for directory, subdirs, filenames in os.walk(application_root, followlinks=False):
        relative_depth = len(Path(directory).relative_to(application_root).parts)
        subdirs[:] = [x for x in subdirs if not (Path(directory) / x).is_symlink()]
        if relative_depth >= 4:
            subdirs[:] = []
        for filename in filenames:
            if filename in known_exes:
                discovered.setdefault(filename, []).append(Path(directory) / filename)

for filename, paths in sorted(discovered.items()):
    for path in paths:
        item = {"name": filename}
        try:
            item["bytes"] = path.stat().st_size
            item["mtime_utc"] = utc(path.stat().st_mtime)
            pe = pefile.PE(str(path), fast_load=True)
            try:
                pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
                versions = set()
                for group in getattr(pe, "FileInfo", []):
                    for info in group:
                        if getattr(info, "Key", None) == b"StringFileInfo":
                            for table in getattr(info, "StringTable", []):
                                value = getattr(table, "entries", {}).get(b"FileVersion", b"")
                                value = value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)
                                if re.fullmatch(r"[0-9][0-9.+_-]{0,96}", value):
                                    versions.add(value)
                item["file_versions"] = sorted(versions)
                item["machine"] = pe.FILE_HEADER.Machine
                item["pe_version_resource_read"] = True
            finally:
                pe.close()
                del pe
        except Exception:
            item["metadata_error"] = "file_changed_unreadable_or_invalid_pe"
            scan_errors += 1
        exe_metadata.append(item)

process_names = {name[:15].lower(): name[:15] for name in known_exes}
for name in ("wine", "wine64", "wine-preloader", "wineserver", "services.exe", "winedevice.exe", "explorer.exe"):
    process_names[name.lower()] = name
process_counts = Counter()
for node in Path("/proc").iterdir():
    if not node.name.isdecimal():
        continue
    try:
        if node.stat().st_uid != os.geteuid():
            continue
        comm = (node / "comm").read_text().strip()
        public_comm = process_names.get(comm.lower())
        if public_comm:
            process_counts[public_comm] += 1
    except (OSError, ValueError):
        pass

groups = {
    "league_logs": [riot_root / "League of Legends/Logs"],
    "riot_logs": [riot_root / "Riot Client/Logs", prefix / "drive_c/users/lab/AppData/Local/Riot Games/Riot Client/Logs"],
    "lab_launcher_logs": [Path("/home/lab/lol-lab")],
}
excluded_log_name = re.compile(r"auth|token|credential|password|account|login|lockfile", re.I)
categories = {
    "disk_full_mentions": re.compile(r"no space left on device|\bENOSPC\b|\bERROR_DISK_FULL\b|\bdisk (?:is )?full\b|not enough (?:free )?disk space", re.I),
    "missing_file_mentions": re.compile(r"\bENOENT\b|file (?:was |is )?not found|no such file or directory|cannot find (?:the )?(?:file|path)", re.I),
    "loader_failure_mentions": re.compile(r"failed to load|could not load|cannot load|import_dll.*not found|LdrInitializeThunk.*failed|NtLoadDriver.*failed", re.I),
    "crash_or_exception_mentions": re.compile(r"unhandled exception|unhandled page fault|segmentation fault|\bSIGSEGV\b|exception code|\baccess violation\b", re.I),
    "out_of_memory_mentions": re.compile(r"out of memory|\bENOMEM\b|\boom-kill\b|cannot allocate memory", re.I),
}
public_dlls = {
    "vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "ucrtbase.dll",
    "d3d11.dll", "dxgi.dll", "d3dcompiler_47.dll", "kernel32.dll", "ntdll.dll",
    "advapi32.dll", "winhttp.dll", "bcrypt.dll", "crypt32.dll", "sechost.dll",
    "wintrust.dll", "riotgamesapi.dll", "rpatch.dll", "libcef.dll", "ffmpeg.dll",
    "libglesv2.dll", "libegl.dll", "nvapi64.dll", "dinput8.dll", "xinput1_4.dll",
}
public_codes = {
    "0x80070070", "0x80070002", "0x80070003", "0x8007000e", "0x80004005",
    "0xc0000005", "0xc000007b", "0xc0000135", "0xc000001d", "0xc0000409",
    "0xe06d7363", "0x80000003",
}
van_allowlist = {"VAN0", "VAN1", "VAN6", "VAN68", "VAN81", "VAN84", "VAN85", "VAN1067", "VAN9001", "VAN9003", "VAN9004", "VAN9005", "VAN9006", "VAN152", "VAN185"}
van_re = re.compile(r"\bVAN[ :#-]*(-?\d{1,5})\b", re.I)
hex_re = re.compile(r"\b0x[0-9a-fA-F]{8}\b")
dll_re = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]{1,80}\.dll)\b", re.I)
technical_context = re.compile(r"error|fail|exception|crash|hresult|vanguard|anti.?cheat|import_dll|loader", re.I)
missing_context = re.compile(r"not found|missing|cannot (?:find|load)|could not (?:find|load)|failed to load|import_dll", re.I)
log_summaries = {}
for group, roots in groups.items():
    candidates = []
    for folder in roots:
        if not folder.is_dir():
            continue
        for directory, subdirs, filenames in os.walk(folder, followlinks=False):
            depth = len(Path(directory).relative_to(folder).parts)
            subdirs[:] = [x for x in subdirs if not (Path(directory) / x).is_symlink()]
            if depth >= (0 if group == "lab_launcher_logs" else 5):
                subdirs[:] = []
            for name in filenames:
                if not name.lower().endswith((".log", ".txt")) or excluded_log_name.search(name):
                    continue
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                try:
                    if path.is_file():
                        candidates.append((path.stat().st_mtime, path))
                except OSError:
                    pass
    counts, codes, vans, dlls = Counter(), Counter(), Counter(), Counter()
    read_count = error_count = line_count = byte_count = 0
    for _, path in sorted(candidates, key=lambda x: x[0], reverse=True)[:24]:
        try:
            with path.open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                total = stream.tell()
                stream.seek(max(0, total - 2 * 1024 * 1024))
                chunk = stream.read(2 * 1024 * 1024)
            byte_count += len(chunk)
            text = chunk.decode("utf-8", "replace")
            for line in text.splitlines():
                line_count += 1
                for category, pattern in categories.items():
                    if pattern.search(line):
                        counts[category] += 1
                if technical_context.search(line):
                    for code in set(x.lower() for x in hex_re.findall(line)) & public_codes:
                        codes[code] += 1
                    for canonical in {"VAN" + suffix for suffix in van_re.findall(line)}:
                        if canonical in van_allowlist:
                            vans[canonical] += 1
                if missing_context.search(line):
                    for dll in set(x.lower() for x in dll_re.findall(line)) & public_dlls:
                        dlls[dll] += 1
            read_count += 1
        except OSError:
            error_count += 1
    log_summaries[group] = {"files_read": read_count, "read_errors_count": error_count, "bytes_examined": byte_count, "lines_examined": line_count, "category_matching_line_counts": dict(sorted(counts.items())), "allowlisted_numeric_code_line_counts": dict(sorted(codes.items())), "allowlisted_van_code_counts": dict(sorted(vans.items())), "allowlisted_missing_dll_line_counts": dict(sorted(dlls.items()))}

try:
    fs = os.statvfs(prefix)
    capacity = {"available_bytes_for_prefix_filesystem": fs.f_bavail * fs.f_frsize}
except OSError:
    capacity = {"unavailable": True}

result = {
    "started_at_utc": started, "completed_at_utc": utc(),
    "scope_alias": "owned_lol_lab_prefix", "collection_mode": "read_only_files_and_proc_comm_no_ui_no_process_start_stop",
    "required_public_executable_presence": {alias: path.is_file() for alias, path in required.items()},
    "public_executable_metadata": exe_metadata, "metadata_errors_count": scan_errors,
    "public_process_comm_counts": dict(sorted(process_counts.items())), "prefix_storage": capacity,
    "sanitized_log_category_summaries": log_summaries,
    "privacy_filter": "Only fixed public executable/process/DLL names, numeric codes from fixed allowlists, timestamps and aggregate counters are exported. No raw lines, log filenames, account identifiers, usernames, URLs, command lines, environment or authentication data are exported.",
    "limits": "Latest up to 24 files per fixed log category, at most 2MiB tail per file. Counters count matching lines, not distinct failures. Process comm names are filtered to fixed public names and the collector UID, without proving association with this Wine prefix. Historical entries and negative matches cannot prove this launch succeeded or failed; files/processes may change during installation or migration.",
}
print(json.dumps(result, indent=2, ensure_ascii=False))
