# Host prepends the read-only common definitions from collect_update_post_migration.py.
technical = re.compile(r"patcher|patching|patch.?state|update|download|launch|install|resume|pause|dependency", re.I)
auth_context = re.compile(r"auth|token|credential|password|account|login|username|email|riot.?id|identity|lockfile|bearer|oauth|entitlement", re.I)
public_words = set("patcher patch patching patcherstate state states oldstate newstate currentstate downloadstate launchstate update updater updating download downloading launch launching launched install installer installation installing installed notinstalled needsinstall needsupdate updaterequired uptodate updated notpatched patchrequired patchingrequired unpatched idle ready available unavailable complete completed failed failure error fatal paused pause pausing resume resumed resuming pending queued waiting retry retrying cancelled canceled stopped stopping running suspended suspend blocked disabled enabled success successful false true none null product products dependency dependencies required missing found notfound valid invalid invalidstate unsupported incompatible inaccessible unable cannot could did not is was has have to from for at on of by and or with without because due reason request requested requests event events status result return returned exit progress bytes total received done remaining verify verifying verification apply applying scoping repair repairing league league_of_legends leagueclient riot riotclient riotclientservices tft live vanguard anticheat anti_cheat vgk vgc enum timestamp timeout connection disconnected connected canlaunch launchable islaunchable isinstalled isready ispaused isupdating isdownloading ispatching iscomplete isinstalling pausedbyuser shouldresume start started starting finish finished abort aborted need needs require requires game executable file files process processes check checking checked operation coordinator pipeline worker task tasks stage stages transition transitioned transferring transfer preflight service services closed open".split())
public_words.update(name.lower().replace(".exe", "").replace(".dll", "") for name in public_files if " " not in name)
enum_values = {x.lower() for x in ("Idle", "Ready", "Pending", "Queued", "Paused", "Pausing", "Resuming", "Downloading", "Patching", "Installing", "Installed", "NotInstalled", "NeedsInstall", "NeedsUpdate", "UpToDate", "Complete", "Completed", "Failed", "Error", "Stopped", "Running", "Suspended", "Blocked", "Disabled", "Available", "Unavailable", "Valid", "Invalid", "Unknown", "Repairing", "Scoping", "Applying")}
enum_field = re.compile(r'\b(state|newState|oldState|currentState|patcherState|downloadState|launchState)\b["\s:=]+([A-Za-z_][A-Za-z0-9_]{0,63})', re.I)
bool_field = re.compile(r'\b(paused|isPaused|canLaunch|launchable|isLaunchable|isInstalled|isReady|isUpdating|isDownloading|isPatching|isComplete|isInstalling|pausedByUser|needsUpdate|updateRequired)\b["\s:=]+(true|false|0|1)\b', re.I)
url_pattern = re.compile(r'\b(?:https?|wss?|ws|ftp|file):(?:/|\\/){2}[^\s<>"\']+', re.I)
email_pattern = re.compile(r"[^\s<>]+@[^\s<>]+")
candidate_paths = []
for folder in roots["riot_updater_logs"]:
    if not folder.is_dir():
        continue
    for directory, subdirs, names in os.walk(folder, followlinks=False):
        subdirs[:] = [x for x in subdirs if not (Path(directory) / x).is_symlink()]
        if len(Path(directory).relative_to(folder).parts) >= 5:
            subdirs[:] = []
        for name in names:
            if not name.lower().endswith((".log", ".txt")) or exclude_name.search(name):
                continue
            path = Path(directory) / name
            try:
                if path.is_file() and not path.is_symlink() and path.stat().st_mtime >= datetime(2026, 10, 12, 13, 55, tzinfo=timezone.utc).timestamp():
                    candidate_paths.append((path.stat().st_mtime, path))
            except OSError:
                pass
events = []
stats = Counter()
anchors = []
event_cutoff = datetime(2026, 10, 12, 13, 55, tzinfo=timezone.utc)
focus_cutoff = datetime(2026, 10, 12, 14, 4, tzinfo=timezone.utc)
for modified, path in sorted(candidate_paths, key=lambda x: x[0], reverse=True)[:4]:
    try:
        with path.open("rb") as stream:
            header = stream.read(65536)
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - 4 * 1024 * 1024))
            lines = stream.read(4 * 1024 * 1024).decode("utf-8", "replace").splitlines()
        stats["files_read"] += 1
        anchor = None
        anchor_match = log_start_time.search(header.decode("utf-8", "replace"))
        elapsed = [float(m.group(1)) for line in lines if (m := elapsed_time.search(line))]
        if anchor_match and elapsed:
            base_time = datetime.fromisoformat(anchor_match.group(1).replace(",", ".").replace("Z", "+00:00"))
            if base_time.tzinfo:
                anchor = base_time.astimezone(timezone.utc)
                anchors.append({"anchor_utc": anchor.isoformat(), "basis": "explicit"})
            else:
                candidates = [base_time.replace(tzinfo=timezone.utc), base_time.replace(tzinfo=timezone(timedelta(hours=-3))).astimezone(timezone.utc)]
                distance, anchor_candidate = min((abs((c + timedelta(seconds=max(elapsed))).timestamp() - modified), c) for c in candidates)
                if distance <= 2:
                    anchor = anchor_candidate
                    anchors.append({"anchor_utc": anchor.isoformat(), "basis": "naive_clock_inferred_with_file_mtime", "difference_seconds": round(distance, 6)})
        for line in lines:
            stats["lines_examined"] += 1
            stamp, basis = line_time(line, anchor)
            if stamp is None or stamp < event_cutoff:
                continue
            if not technical.search(line):
                continue
            if auth_context.search(line):
                stats["technical_lines_excluded_for_auth_or_identity_context"] += 1
                continue
            clean = url_pattern.sub(" ", line)
            clean = email_pattern.sub(" ", clean)
            tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", clean)
            rendered = []
            for token in tokens:
                value = token.lower()
                safe = value if value in public_words else "[redacted]"
                if not rendered or safe != "[redacted]" or rendered[-1] != "[redacted]":
                    rendered.append(safe)
            enums = [{"field": field.lower(), "value": value.lower()} for field, value in enum_field.findall(clean) if value.lower() in enum_values]
            bools = [{"field": field.lower(), "value": value.lower() in ("true", "1")} for field, value in bool_field.findall(clean)]
            public_codes = sorted(set(x.lower() for x in hex_codes.findall(clean)) & codes_allowlist)
            basenames = sorted(name for name, pattern in file_patterns.items() if file_context.search(clean) and pattern.search(clean))
            events.append({"timestamp_utc": stamp.isoformat(), "period": "since_11_04_local" if stamp >= focus_cutoff else "before_11_04_local", "timestamp_basis": basis, "closed_vocabulary_message": " ".join(rendered)[:900], "public_enum_fields": enums, "public_boolean_fields": bools, "allowlisted_codes": public_codes, "allowlisted_missing_public_basenames": basenames})
    except (OSError, ValueError):
        stats["read_or_timestamp_error_count"] += 1
events.sort(key=lambda x: x["timestamp_utc"])
print(json.dumps({"collected_at_utc": datetime.now(timezone.utc).isoformat(), "scope_alias": "owned_rcs_updater_launch", "event_cutoff_utc": event_cutoff.isoformat(), "focus_cutoff_utc": focus_cutoff.isoformat(), "anchors": anchors, "read_summary": dict(stats), "selected_events_total_before_cap": len(events), "events_last_200": events[-200:], "privacy_policy": "Closed vocabulary only: every unknown word or identifier is replaced. No raw lines, numbers from unlisted fields, account data, URLs, emails, tokens, process arguments, auth configuration, lockfiles or file paths are exported. Auth/identity-context lines excluded entirely.", "limits": "Timed recent technical events only. Closed-vocabulary rendering can omit decisive details; no causal or blocking claim follows from absence of a retained error. Timestamps anchored as recorded, with naive-clock inference only when within two seconds of mtime. No UI actions, guest writes or process starts/stops."}, indent=2))
