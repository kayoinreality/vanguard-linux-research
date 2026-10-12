"""Export only timestamp-shape counters and known log-start timestamp values."""
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

base = Path("/home/lab/lol-lab/prefix/drive_c")
roots = [base / "Riot Games/Riot Client/Logs", base / "users/lab/AppData/Local/Riot Games/Riot Client/Logs"]
cutoff = datetime(2026, 10, 12, 13, 38, tzinfo=timezone.utc).timestamp()
iso = r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,9})?(?:Z|[+-]\d{2}:?\d{2})?"
anchor_pattern = re.compile(r"logging started at\s*[:=]?\s*(" + iso + ")", re.I)
elapsed_pattern = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*\|")
excluded = re.compile(r"auth|token|credential|password|account|login|lockfile", re.I)
candidates = []
for root in roots:
    if not root.is_dir():
        continue
    for directory, subdirs, files in os.walk(root, followlinks=False):
        if len(Path(directory).relative_to(root).parts) >= 5:
            subdirs[:] = []
        for name in files:
            if not name.lower().endswith((".log", ".txt")) or excluded.search(name):
                continue
            path = Path(directory) / name
            try:
                if path.is_file() and not path.is_symlink() and path.stat().st_mtime >= cutoff:
                    candidates.append((path.stat().st_mtime, path))
            except OSError:
                pass
results = []
for modified, path in sorted(candidates, key=lambda x: x[0], reverse=True)[:8]:
    try:
        with path.open("rb") as stream:
            header = stream.read(65536)
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - 4 * 1024 * 1024))
            tail = stream.read(4 * 1024 * 1024)
        shapes = Counter()
        elapsed = []
        anchors = sorted(set(anchor_pattern.findall(header.decode("utf-8", "replace"))))
        for line in tail.decode("utf-8", "replace").splitlines():
            match = elapsed_pattern.search(line)
            if match:
                shapes["relative_elapsed_pipe"] += 1
                elapsed.append(float(match.group(1)))
            elif line.lstrip().startswith("{"):
                shapes["json_like"] += 1
            elif re.search(iso, line):
                shapes["iso_date_somewhere"] += 1
            else:
                shapes["other"] += 1
        results.append({"mtime_utc": datetime.fromtimestamp(modified, timezone.utc).isoformat(), "shape_counts": dict(shapes), "known_logging_start_timestamp_strings": anchors, "minimum_elapsed_seconds": min(elapsed) if elapsed else None, "maximum_elapsed_seconds": max(elapsed) if elapsed else None})
    except OSError:
        results.append({"read_error": True})
print(json.dumps({"timestamp_format_inventory_only": results, "raw_lines_exported": False}, indent=2))
