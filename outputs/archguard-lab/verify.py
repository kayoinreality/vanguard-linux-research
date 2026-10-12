#!/usr/bin/env python3
"""Behavioral integration checks against the real installed lab service."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import socket
import subprocess
import sys
import tempfile
import time

TARGET = Path("/var/lib/archguard-lab/demo.bin")
MANIFEST = Path("/etc/archguard-lab/manifest.json")
SOCKET = "/run/archguard-lab/control.sock"
EXPECTED = b"ArchGuard original lab fixture v1\n"
REPORT = Path(__file__).resolve().parent / "validation.json"
checks = []


def raw_query(payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(4)
        connection.connect(SOCKET)
        connection.sendall(payload)
        with connection.makefile("rb") as reader:
            result = reader.readline(131072)
    return json.loads(result)


def query(operation):
    return raw_query(json.dumps({"op": operation}).encode() + b"\n")


def expect_state(name, wanted, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = query("status")
        current = response["files"][0]["state"]
        if current in wanted:
            assert response["health"] == "running", response
            assert response["integrity"] == ("clean" if current == "clean" else "alert"), response
            checks.append({"test": name, "passed": True, "observed": current, "checked_at": response["checked_at"]})
            return response
        time.sleep(0.1)
    raise AssertionError(f"{name}: expected {wanted}, got {response}")


def restore():
    if TARGET.exists() or TARGET.is_symlink():
        TARGET.unlink()
    TARGET.write_bytes(EXPECTED)
    TARGET.chmod(0o644)


def main():
    if os.geteuid() != 0:
        raise RuntimeError("Run via sudo inside the dedicated lab VM")
    assert subprocess.check_output(["systemd-detect-virt"], text=True).strip() == "microsoft"
    assert not TARGET.is_symlink() and TARGET.read_bytes() == EXPECTED, "Fixture is not the original lab file; refusing to modify it"
    original_manifest = MANIFEST.read_bytes()
    document = json.loads(original_manifest)
    reference = document["files"][0]["sha256"]
    independent = subprocess.check_output(["sha256sum", str(TARGET)], text=True).split()[0]
    assert reference == independent == hashlib.sha256(EXPECTED).hexdigest()
    error = None
    try:
        assert query("ping") == {"ok": True, "version": "0.1.0", "service": "archguard-lab"}
        checks.append({"test": "client_service_handshake", "passed": True})
        service_pid = int(subprocess.check_output(["systemctl", "show", "archguard-lab.service", "-p", "MainPID", "--value"], text=True))
        assert service_pid > 0
        assert os.stat(f"/proc/{service_pid}").st_uid == pwd.getpwnam("archguard-lab").pw_uid != 0
        checks.append({"test": "daemon_runs_as_dedicated_non_root_user", "passed": True, "pid": service_pid})
        expect_state("unchanged_file_and_independent_hash", {"clean"})

        changed = bytes([EXPECTED[0] ^ 1]) + EXPECTED[1:]
        assert len(changed) == len(EXPECTED)
        TARGET.write_bytes(changed)
        expect_state("same_size_modification_detected_by_background_monitor", {"modified"})
        subprocess.run(["systemctl", "restart", "archguard-lab.service"], check=True)
        # Allow the process to bind after systemd's simple service transition.
        for _ in range(30):
            try:
                if query("ping").get("ok"):
                    break
            except OSError:
                time.sleep(0.1)
        expect_state("modified_file_stays_modified_after_restart", {"modified"})
        assert MANIFEST.read_bytes() == original_manifest
        checks.append({"test": "trusted_reference_not_reenrolled_on_restart", "passed": True})

        TARGET.unlink()
        expect_state("deleted_target_never_reports_clean", {"missing"})
        with tempfile.TemporaryDirectory(prefix="archguard-check-", dir=TARGET.parent) as temporary:
            decoy = Path(temporary) / "same-content.bin"
            decoy.write_bytes(EXPECTED)
            TARGET.symlink_to(decoy)
            expect_state("symlink_with_correct_content_is_rejected", {"unavailable", "unsafe"})
            TARGET.unlink()
        os.mkfifo(TARGET)
        expect_state("fifo_is_rejected_without_blocking", {"unsafe"})
        TARGET.unlink()
        with TARGET.open("wb") as oversized:
            oversized.truncate(16 * 1024 * 1024 + 1)
        expect_state("oversized_target_is_unavailable", {"unavailable"})
        restore()
        expect_state("exact_restoration_recovers_clean_state", {"clean"})

        for name, payload in [
            ("malformed_json_rejected", b"not-json\n"),
            ("unknown_operation_rejected", b'{"op":"update_baseline"}\n'),
            ("client_cannot_supply_arbitrary_file_paths", b'{"op":"check","path":"/etc/passwd"}\n'),
            ("oversized_message_rejected", b"x" * 4097 + b"\n"),
        ]:
            answer = raw_query(payload)
            assert answer.get("ok") is False and "error" in answer, answer
            assert query("ping")["ok"] is True
            checks.append({"test": name, "passed": True, "error": answer["error"]})
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as slow:
            slow.connect(SOCKET)
            time.sleep(0.1)
            begin = time.monotonic()
            assert query("ping")["ok"] is True
            elapsed = time.monotonic() - begin
            assert elapsed < 2.5, elapsed
            checks.append({"test": "silent_client_is_bounded_by_timeout", "passed": True, "seconds": round(elapsed, 3)})

        denial = subprocess.run(["runuser", "-u", "nobody", "--", "python", "-c", "import socket; s=socket.socket(socket.AF_UNIX); s.connect('/run/archguard-lab/control.sock')"], capture_output=True, text=True)
        assert denial.returncode != 0 and "PermissionError" in denial.stderr, denial
        checks.append({"test": "user_outside_socket_group_is_denied", "passed": True})
        expect_state("final_service_and_fixture_are_healthy", {"clean"})
    except Exception as failure:
        error = f"{type(failure).__name__}: {failure}"
        raise
    finally:
        restore()
        if not subprocess.run(["systemctl", "is-active", "--quiet", "archguard-lab.service"]).returncode == 0:
            subprocess.run(["systemctl", "restart", "archguard-lab.service"], check=True)
        report = {
            "prototype": "ArchGuard Lab", "version": "0.1.0",
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "kernel": os.uname().release, "passed": error is None,
            "checks": checks, "error": error,
            "scope": "Original userspace service; own fixture only; no Riot component or kernel driver executed.",
        }
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "checks": len(checks), "report": str(REPORT)}))


if __name__ == "__main__":
    main()
