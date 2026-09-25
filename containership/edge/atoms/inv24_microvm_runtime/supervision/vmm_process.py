"""VMM process supervision (MC-001-I03, MC-001-I06).

Starts the (digest-verified) VMM with an argv list — never ``shell=True`` —
records PID/start time/version, captures bounded stdout/stderr, detects
premature exit, enforces a deadline, and deterministically reaps the child
and removes its API socket and temporary files on every exit path.
"""
from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field

from ..errors import Inv24Error

MAX_CAPTURE = 64 * 1024


class _BoundedBuffer:
    def __init__(self, limit: int = MAX_CAPTURE) -> None:
        self.limit, self.data, self.truncated = limit, bytearray(), False
        self._lock = threading.Lock()

    def feed(self, stream) -> None:
        for chunk in iter(lambda: stream.read(4096), b""):
            with self._lock:
                room = self.limit - len(self.data)
                if room > 0:
                    self.data += chunk[:room]
                if len(chunk) > room:
                    self.truncated = True

    def text(self) -> str:
        with self._lock:
            return self.data.decode("utf-8", "replace")


@dataclass
class ProcessRecord:
    pid: int
    started_at: float
    argv0: str
    version: str
    socket_path: str
    exit_code: int | None = None
    cleanup: dict[str, bool] = field(default_factory=dict)


class VmmProcess:
    """One supervised VMM child; use as a context manager for guaranteed cleanup."""

    def __init__(self, argv: list[str], *, socket_path: str, version: str,
                 env: dict[str, str] | None = None, workdir: str | None = None,
                 ready_timeout_s: float = 2.0, stop_timeout_s: float = 2.0) -> None:
        if not argv or not all(isinstance(a, str) for a in argv):
            raise Inv24Error("CONFIG_REJECTED", "argv must be a non-empty list of strings")
        if not os.path.isabs(argv[0]):
            raise Inv24Error("ARTIFACT_NOT_APPROVED", "VMM executable must be an absolute verified path")
        if len(socket_path.encode()) > 107:
            raise Inv24Error("CONFIG_REJECTED", "API socket path exceeds sun_path limit")
        self.argv, self.socket_path, self.version = list(argv), socket_path, version
        self.env = {"PATH": "/usr/bin:/bin", **(env or {})}  # minimal, explicit environment
        self.workdir = workdir or tempfile.mkdtemp(prefix="inv24-vmm-")
        self._own_workdir = workdir is None
        self.ready_timeout_s, self.stop_timeout_s = ready_timeout_s, stop_timeout_s
        self.proc: subprocess.Popen | None = None
        self.stdout, self.stderr = _BoundedBuffer(), _BoundedBuffer()
        self.record: ProcessRecord | None = None
        self._threads: list[threading.Thread] = []

    def start(self) -> ProcessRecord:
        if self.proc is not None:
            raise Inv24Error("CONFIG_REJECTED", "process already started")
        try:
            self.proc = subprocess.Popen(self.argv, shell=False, env=self.env, cwd=self.workdir,
                                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, close_fds=True,
                                         start_new_session=True)
        except OSError as exc:
            self.cleanup()
            raise Inv24Error("PROCESS_CRASHED", f"spawn failed: {exc.strerror}") from None
        for buf, stream in ((self.stdout, self.proc.stdout), (self.stderr, self.proc.stderr)):
            t = threading.Thread(target=buf.feed, args=(stream,), daemon=True)
            t.start()
            self._threads.append(t)
        self.record = ProcessRecord(self.proc.pid, time.time(), os.path.basename(self.argv[0]),
                                    self.version, self.socket_path)
        return self.record

    def wait_ready(self, probe=None) -> None:
        """Wait until the API socket exists (or ``probe()`` is true); detect early exit."""
        deadline = time.monotonic() + self.ready_timeout_s
        probe = probe or (lambda: os.path.exists(self.socket_path))
        while time.monotonic() < deadline:
            if self.proc is None or self.proc.poll() is not None:
                code = None if self.proc is None else self.proc.returncode
                raise Inv24Error("PROCESS_CRASHED", f"VMM exited before ready (code {code})")
            if probe():
                return
            time.sleep(0.01)
        raise Inv24Error("TIMEOUT", "VMM did not become ready before the deadline")

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> int | None:
        if self.proc is None:
            return None
        if self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.proc.wait(self.stop_timeout_s)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.proc.wait(self.stop_timeout_s)
        for t in self._threads:
            t.join(1.0)
        for stream in (self.proc.stdout, self.proc.stderr):
            if stream is not None:
                stream.close()
        if self.record:
            self.record.exit_code = self.proc.returncode
        return self.proc.returncode

    def cleanup(self) -> dict[str, bool]:
        """Idempotent: reap child, remove socket and owned workdir. Raises if any step fails."""
        result = {"reaped": True, "socket_removed": True, "workdir_removed": True}
        try:
            self.stop()
        except Exception:
            result["reaped"] = False
        try:
            if os.path.lexists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError:
            result["socket_removed"] = False
        if self._own_workdir:
            import shutil
            shutil.rmtree(self.workdir, ignore_errors=True)
            result["workdir_removed"] = not os.path.exists(self.workdir)
        if self.record:
            self.record.cleanup = result
        if not all(result.values()):
            raise Inv24Error("CLEANUP_FAILED", f"cleanup incomplete: {result}")
        return result

    def __enter__(self) -> "VmmProcess":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()


def reap_orphan_sockets(directory: str, live_sockets: set[str]) -> list[str]:
    """Remove ``*.sock`` files in ``directory`` not owned by a live supervisor."""
    removed = []
    for p in pathlib.Path(directory).glob("*.sock"):
        if str(p) not in live_sockets:
            try:
                p.unlink()
                removed.append(str(p))
            except OSError:
                pass
    return removed
