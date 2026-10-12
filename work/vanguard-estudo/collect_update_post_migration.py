"""Read fixed log roots; export only aggregate technical allowlist results."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import pwd
import re

if os.geteuid() != pwd.getpwnam("lab").pw_uid:
    raise RuntimeError("Wrong collector UID")

cutoff = datetime(2026, 10, 12, 13, 38, tzinfo=timezone.utc)
started = datetime.now(timezone.utc)
prefix = Path("/home/lab/lol-lab/prefix")
riot_root = prefix / "drive_c/Riot Games"
roots = {
    "riot_updater_logs": [riot_root / "Riot Client/Logs", prefix / "drive_c/users/lab/AppData/Local/Riot Games/Riot Client/Logs"],
    "league_logs": [riot_root / "League of Legends/Logs"],
    "launcher_logs": [Path("/home/lab/lol-lab")],
}
exclude_name = re.compile(r"auth|token|credential|password|account|login|lockfile", re.I)
iso_value = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,9})?(?:Z|[+-]\d{2}:?\d{2})?"
header_time = re.compile(r"^\s*(?:\[\s*)?(" + iso_value + r")")
json_time = re.compile(r'^\s*\{.{0,100}?"(?:timestamp|time|ts)"\s*:\s*"(' + iso_value + r')"')
explicit_zone = re.compile(r"(?:Z|[+-]\d{2}:?\d{2})$")
elapsed_time = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*\|")
log_start_time = re.compile(r"logging started at\s*[:=]?\s*(" + iso_value + r")", re.I)
patterns = {
    "disk_full_mentions": re.compile(r"no space left on device|\bENOSPC\b|\bERROR_DISK_FULL\b|\bdisk (?:is )?full\b", re.I),
    "insufficient_space_mentions": re.compile(r"insufficient[^\n]{0,35}space|not enough (?:available |free )?(?:disk |storage )?space|space (?:check|requirement)[^\n]{0,50}(?:fail|not enough)", re.I),
    "permission_mentions": re.compile(r"permission denied|access (?:is )?denied|\bEACCES\b|\bEPERM\b|\bERROR_ACCESS_DENIED\b", re.I),
    "patcher_or_update_mentions": re.compile(r"\bpatch(?:er|ing)?\b|\bupdat(?:e|er|ing)\b|\bdownload(?:ing)?\b|\binstall(?:er|ation|ing)\b", re.I),
    "network_error_mentions": re.compile(r"network[^\n]{0,60}(?:fail|error|unavailable)|(?:connection|request)[^\n]{0,40}timed? out|\btimeout\b|DNS[^\n]{0,40}(?:fail|error)|could not resolve|failed to connect|connection refused", re.I),
    "pause_or_resume_mentions": re.compile(r"\bpause(?:d)?\b|\bresume(?:d)?\b|\bpausing\b|\bresuming\b", re.I),
    "fatal_mentions": re.compile(r"\bfatal\b|\bfatal_error\b|\bunrecoverable\b|abort(?:ed|ing)? (?:patch|update|download|install)", re.I),
    "missing_file_mentions": re.compile(r"\bENOENT\b|file (?:was |is )?not found|no such file or directory|cannot find (?:the )?(?:file|path)|\bmissing\b", re.I),
}
codes_allowlist = {"0x80070070", "0x80070027", "0x80070002", "0x80070003", "0x80070005", "0x8007000e", "0x80004005", "0x80072ee2", "0x80072ee7", "0x80072efd", "0x80072f8f", "0xc0000005", "0xc000007b", "0xc0000135", "0xc000001d", "0xc0000409", "0xe06d7363", "0x80000003"}
hex_codes = re.compile(r"\b0x[0-9a-fA-F]{8}\b")
van_allowlist = {"VAN0", "VAN1", "VAN6", "VAN68", "VAN81", "VAN84", "VAN85", "VAN1067", "VAN9001", "VAN9003", "VAN9004", "VAN9005", "VAN9006", "VAN152", "VAN185"}
van_codes = re.compile(r"\bVAN[ :#-]*(-?\d{1,5})\b", re.I)
http_status = re.compile(r"\bHTTP(?:/\d(?:\.\d)?)?\s*(?:status|code|response)?\s*[:=]?\s*(408|429|500|502|503|504)\b", re.I)
code_context = re.compile(r"error|fail|exception|crash|hresult|vanguard|anti.?cheat|import_dll|loader", re.I)
file_context = re.compile(r"not found|missing|cannot (?:find|load)|could not (?:find|load)|failed to load|import_dll|no such file", re.I)
public_files = {"LeagueClient.exe", "LeagueClientUx.exe", "LeagueClientUxRender.exe", "League of Legends.exe", "RiotClientServices.exe", "RiotClientUx.exe", "RiotClientUxRender.exe", "vgk.sys", "vgc.exe", "vgm.exe", "vgrl.dll", "vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "ucrtbase.dll", "d3d11.dll", "dxgi.dll", "d3dcompiler_47.dll", "kernel32.dll", "ntdll.dll", "advapi32.dll", "winhttp.dll", "bcrypt.dll", "crypt32.dll", "wintrust.dll", "RiotGamesApi.dll", "rpatch.dll", "libcef.dll", "ffmpeg.dll", "libGLESv2.dll", "libEGL.dll", "nvapi64.dll", "dinput8.dll", "xinput1_4.dll"}
file_patterns = {name: re.compile(r"(?<![A-Za-z0-9_.-])" + re.escape(name) + r"(?![A-Za-z0-9_.-])", re.I) for name in public_files}

def line_time(line, anchor=None):
    match = header_time.search(line) or json_time.search(line)
    if not match:
        elapsed = elapsed_time.search(line)
        if elapsed and anchor is not None:
            return anchor + timedelta(seconds=float(elapsed.group(1))), "relative_elapsed_header_anchor"
        return None, "no_supported_header_timestamp"
    value = match.group(1)
    if not explicit_zone.search(value):
        return None, "naive_timestamp_ignored"
    try:
        return datetime.fromisoformat(value.replace(",", ".").replace("Z", "+00:00")).astimezone(timezone.utc), "explicit_timestamp"
    except ValueError:
        return None, "timestamp_parse_error"

summaries = {}
for group, folders in roots.items():
    candidates = []
    for folder in folders:
        if not folder.is_dir():
            continue
        for directory, subdirs, names in os.walk(folder, followlinks=False):
            depth = len(Path(directory).relative_to(folder).parts)
            subdirs[:] = [x for x in subdirs if not (Path(directory) / x).is_symlink()]
            if depth >= (0 if group == "launcher_logs" else 5):
                subdirs[:] = []
            for name in names:
                if not name.lower().endswith((".log", ".txt")) or exclude_name.search(name):
                    continue
                path = Path(directory) / name
                try:
                    if not path.is_symlink() and path.is_file() and path.stat().st_mtime >= cutoff.timestamp():
                        candidates.append((path.stat().st_mtime, path))
                except OSError:
                    pass
    counts, codes, vans, files, http, ignored, time_basis = (Counter() for _ in range(7))
    read_count = error_count = line_count = included = before_cutoff = byte_count = 0
    first_ts = last_ts = None
    anchors_used = []
    for _, path in sorted(candidates, key=lambda x: x[0], reverse=True)[:24]:
        try:
            with path.open("rb") as stream:
                header = stream.read(65536)
                stream.seek(0, os.SEEK_END)
                stream.seek(max(0, stream.tell() - 4 * 1024 * 1024))
                chunk = stream.read(4 * 1024 * 1024)
            byte_count += len(chunk)
            lines = chunk.decode("utf-8", "replace").splitlines()
            anchor = None
            start_match = log_start_time.search(header.decode("utf-8", "replace"))
            elapsed_values = [float(match.group(1)) for line in lines if (match := elapsed_time.search(line))]
            if start_match and elapsed_values:
                raw_start = start_match.group(1)
                parsed_start = datetime.fromisoformat(raw_start.replace(",", ".").replace("Z", "+00:00"))
                if parsed_start.tzinfo is not None:
                    anchor = parsed_start.astimezone(timezone.utc)
                    anchors_used.append({"anchor_utc": anchor.isoformat(), "basis": "explicit_offset_in_log_start"})
                else:
                    local_candidate = parsed_start.replace(tzinfo=timezone(timedelta(hours=-3))).astimezone(timezone.utc)
                    utc_candidate = parsed_start.replace(tzinfo=timezone.utc)
                    modified = path.stat().st_mtime
                    clock_candidates = [(abs((candidate + timedelta(seconds=max(elapsed_values))).timestamp() - modified), label, candidate) for label, candidate in (("America/Sao_Paulo_minus03", local_candidate), ("UTC", utc_candidate))]
                    distance, label, best = min(clock_candidates, key=lambda x: x[0])
                    if distance <= 2.0:
                        anchor = best
                        anchors_used.append({"anchor_utc": anchor.isoformat(), "basis": "naive_log_start_clock_inferred_by_last_elapsed_and_file_mtime", "clock_basis": label, "last_elapsed_vs_mtime_difference_seconds": round(distance, 6)})
            for line in lines:
                line_count += 1
                stamp, kind = line_time(line, anchor)
                if stamp is None:
                    ignored[kind] += 1
                    continue
                if stamp < cutoff:
                    before_cutoff += 1
                    continue
                if stamp > datetime.now(timezone.utc) + timedelta(minutes=2):
                    ignored["future_timestamp_ignored"] += 1
                    continue
                included += 1
                time_basis[kind] += 1
                first_ts = stamp if first_ts is None else min(first_ts, stamp)
                last_ts = stamp if last_ts is None else max(last_ts, stamp)
                for category, pattern in patterns.items():
                    if pattern.search(line):
                        counts[category] += 1
                if code_context.search(line):
                    for code in set(x.lower() for x in hex_codes.findall(line)) & codes_allowlist:
                        codes[code] += 1
                    for van in {"VAN" + suffix for suffix in van_codes.findall(line)} & van_allowlist:
                        vans[van] += 1
                for status in set(http_status.findall(line)):
                    http[status] += 1
                if file_context.search(line):
                    for name, pattern in file_patterns.items():
                        if pattern.search(line):
                            files[name] += 1
            read_count += 1
        except OSError:
            error_count += 1
    summaries[group] = {"files_read": read_count, "read_errors_count": error_count, "bytes_examined": byte_count, "lines_examined": line_count, "lines_with_supported_time_in_window": included, "timestamp_basis_line_counts": dict(sorted(time_basis.items())), "log_start_anchors_used": anchors_used, "lines_before_cutoff_ignored": before_cutoff, "other_timestamp_lines_ignored": dict(sorted(ignored.items())), "first_included_timestamp_utc": first_ts.isoformat() if first_ts else None, "last_included_timestamp_utc": last_ts.isoformat() if last_ts else None, "category_matching_line_counts": dict(sorted(counts.items())), "allowlisted_numeric_code_line_counts": dict(sorted(codes.items())), "allowlisted_van_code_line_counts": dict(sorted(vans.items())), "allowlisted_http_error_status_line_counts": dict(sorted(http.items())), "allowlisted_missing_public_basename_line_counts": dict(sorted(files.items()))}

storage = {}
for alias, path in (("root", Path("/")), ("game", riot_root / "League of Legends")):
    try:
        stat = os.statvfs(path)
        storage[alias] = {"available_bytes": stat.f_bavail * stat.f_frsize}
    except OSError:
        storage[alias] = {"unavailable": True}

print(json.dumps({"started_at_utc": started.isoformat(), "completed_at_utc": datetime.now(timezone.utc).isoformat(), "cutoff_utc": cutoff.isoformat(), "cutoff_local_context": "2026-10-12 10:38:00 America/Sao_Paulo", "scope_alias": "owned_lol_updater_after_migration", "mode": "read_only_logs_and_storage_no_ui_no_start_stop", "ui_context_from_task": "Download was reported active at 10:49 local; this log snapshot does not diagnose a current pause", "storage_summary": storage, "sanitized_log_summaries": summaries, "privacy_filter": "Only fixed categories, fixed public basename/code allowlists, timestamps and numeric counters are emitted. No raw lines, filenames of logs, account identifiers, usernames, tokens, URLs or account paths are exported.", "limits": "Category counts require an explicit-offset header timestamp or relative elapsed time anchored to the known logging-start header. A naive start-header clock is inferred only when local-minus03 or UTC predicts the latest elapsed record within two seconds of file mtime; this assumption is recorded per anchor. Untimed continuations and unsupported timestamps are ignored. Latest up to 24 log files per category modified after cutoff; at most 4MiB tail plus 64KiB start-header per file. Counts are matching lines, not distinct events or causal diagnoses. Historical or negative matches cannot establish a current updater block."}, indent=2, ensure_ascii=False))
