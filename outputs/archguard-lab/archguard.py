#!/usr/bin/env python3
"""Original Linux lab prototype: local IPC and a fixed-file integrity monitor."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import socketserver
import stat
import threading
import time

VERSION = "0.1.0"
DATA_DIR = Path("/var/lib/archguard-lab")
SOCKET = Path("/run/archguard-lab/control.sock")
CONFIG = Path("/etc/archguard-lab/manifest.json")
MAX_FILE = 16 * 1024 * 1024
MAX_REQUEST = 4096


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def log(event, **fields):
    print(json.dumps({"time": utc_now(), "event": event, **fields}), flush=True)


def load_manifest(path):
    with path.open("rb") as source:
        raw = source.read(65537)
    if len(raw) > 65536:
        raise ValueError("Manifest exceeds 64 KiB")
    document = json.loads(raw)
    if not isinstance(document, dict) or type(document.get("version")) is not int or document.get("version") != 1:
        raise ValueError("Unsupported manifest")
    files = document.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= 8:
        raise ValueError("Expected 1–8 lab files")
    names = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Invalid file entry")
        name, digest = item.get("name", ""), item.get("sha256", "")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
            raise ValueError("Only direct lab filenames are accepted")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid SHA-256 reference")
        if name in names:
            raise ValueError("Duplicate lab filename")
        names.add(name)
    return [{"name": item["name"], "sha256": item["sha256"]} for item in files]


def inspect_file(item):
    result = {"name": item["name"], "expected_sha256": item["sha256"]}
    try:
        # Reject symlinks and avoid blocking on a substituted FIFO/device.
        descriptor = os.open(DATA_DIR / item["name"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb", buffering=0) as source:
            before = os.fstat(source.fileno())
            if not stat.S_ISREG(before.st_mode):
                return {**result, "state": "unsafe", "reason": "not_regular"}
            if before.st_size > MAX_FILE:
                return {**result, "state": "unavailable", "reason": "size_limit"}
            digest = hashlib.sha256()
            read_bytes = 0
            while block := source.read(65536):
                read_bytes += len(block)
                if read_bytes > MAX_FILE:
                    return {**result, "state": "unavailable", "reason": "size_limit"}
                digest.update(block)
            after = os.fstat(source.fileno())
        current = os.stat(DATA_DIR / item["name"], follow_symlinks=False)
        identity = lambda entry: (entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns, entry.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            return {**result, "state": "unavailable", "reason": "changed_during_read"}
        actual = digest.hexdigest()
        return {**result, "state": "clean" if actual == item["sha256"] else "modified", "observed_sha256": actual, "bytes": read_bytes}
    except FileNotFoundError:
        return {**result, "state": "missing"}
    except OSError as error:
        return {**result, "state": "unavailable", "errno": error.errno}


class Monitor:
    def __init__(self, entries):
        self.entries = entries
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.checked = 0
        self.snapshot = None
        self.previous_states = None

    def check(self):
        with self.lock:
            results = [inspect_file(entry) for entry in self.entries]
            states = tuple((item["name"], item["state"]) for item in results)
            self.checked = time.monotonic()
            self.snapshot = {"checked_at": utc_now(), "integrity": "clean" if all(item["state"] == "clean" for item in results) else "alert", "files": results}
            if states != self.previous_states:
                log("integrity_transition", integrity=self.snapshot["integrity"], files=[{"name": name, "state": state} for name, state in states])
                self.previous_states = states
            return self.view_locked()

    def view_locked(self):
        age = time.monotonic() - self.checked
        return {"ok": True, "version": VERSION, "health": "running" if age <= 3 else "stale", "uptime_seconds": round(time.monotonic() - self.started, 3), "check_age_seconds": round(age, 3), **self.snapshot}

    def status(self):
        with self.lock:
            return self.view_locked()


class RequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(1)
        response = {"ok": False, "error": "invalid_request"}
        try:
            request = self.rfile.readline(MAX_REQUEST + 1)
            if len(request) > MAX_REQUEST or not request.endswith(b"\n"):
                response = {"ok": False, "error": "invalid_frame"}
            else:
                document = json.loads(request)
                if not isinstance(document, dict) or set(document) != {"op"}:
                    response = {"ok": False, "error": "invalid_request"}
                elif document["op"] == "ping":
                    response = {"ok": True, "version": VERSION, "service": "archguard-lab"}
                elif document["op"] == "status":
                    response = self.server.monitor.status()
                elif document["op"] == "check":
                    response = self.server.monitor.check()
                else:
                    response = {"ok": False, "error": "unknown_operation"}
        except (ValueError, UnicodeError):
            pass
        except socket.timeout:
            response = {"ok": False, "error": "request_timeout"}
        try:
            self.wfile.write(json.dumps(response).encode("utf-8") + b"\n")
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass


def serve(manifest):
    entries = load_manifest(manifest)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    monitor = Monitor(entries)
    watcher_failed = threading.Event()
    monitor.check()
    with (SOCKET.parent / "service.lock").open("a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if SOCKET.exists() or SOCKET.is_symlink():
            info = SOCKET.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise RuntimeError("Refusing to replace a foreign or non-socket path")
            SOCKET.unlink()
        with socketserver.UnixStreamServer(str(SOCKET), RequestHandler) as server:
            os.chmod(SOCKET, 0o660)
            socket_inode = SOCKET.lstat().st_ino
            server.monitor = monitor
            server.timeout = 0.2

            def watch():
                while not stop.wait(1):
                    try:
                        monitor.check()
                    except Exception as error:
                        log("monitor_error", error_type=type(error).__name__)
                        watcher_failed.set()
                        stop.set()

            watcher = threading.Thread(target=watch, daemon=True)
            watcher.start()
            log("started", version=VERSION, uid=os.getuid(), socket=str(SOCKET), targets=len(entries))
            try:
                while not stop.is_set():
                    server.handle_request()
            finally:
                stop.set()
                watcher.join(timeout=2)
                if SOCKET.exists() and SOCKET.lstat().st_ino == socket_inode:
                    SOCKET.unlink()
                log("stopped")
    if watcher_failed.is_set():
        raise RuntimeError("Integrity monitor failed unexpectedly")


def query(operation):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(4)
        connection.connect(str(SOCKET))
        connection.sendall(json.dumps({"op": operation}).encode("utf-8") + b"\n")
        with connection.makefile("rb") as response:
            payload = response.readline(65537)
        if len(payload) > 65536 or not payload.endswith(b"\n"):
            raise RuntimeError("Invalid service response")
    return json.loads(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["serve", "ping", "status", "check"])
    parser.add_argument("--manifest", type=Path, default=CONFIG)
    args = parser.parse_args()
    if args.operation == "serve":
        serve(args.manifest)
        return 0
    try:
        result = query(args.operation)
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"ok": False, "error": "service_unavailable", "detail": str(error)}))
        return 2
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        return 2
    if result.get("health") == "stale" or result.get("integrity") == "alert":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
