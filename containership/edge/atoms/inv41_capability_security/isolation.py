"""Process-isolation profile and capability bridge (Section 10, REQ-ISO-*).

The in-process primitives are a *logical* capability boundary.  For hostile
code this module provides the next layer that pure Python can honestly offer:

* ``run_isolated`` executes untrusted code in a separate interpreter process
  (``-I -S -B``, empty environment, private temp cwd, POSIX rlimits for CPU,
  address space, open files, processes and file size, closed fds, wall-clock
  timeout with kill).  The trusted authority implementation is never imported
  into that process; the child only sees opaque handles.
* ``CapabilityBridge`` converts requests from the isolated side into local
  capability operations.  Handles are random, bound to one session, principal
  and authority domain, never derived from a Reference, and die with the
  session or the membrane behind them.

NOT provided here (and therefore BLOCKED for production adversarial work, see
BLOCKERS.json): network/filesystem namespaces, seccomp/AppContainer syscall
filters, Wasm/WASI or microVM runtimes.  ``profile_status()`` reports that.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
from typing import Final

from .capabilities import CapabilityError, Holder, Membrane, Reference
from .errors import AuthenticationFailed, describe

DEFAULT_LIMITS: Final[dict] = {"cpu_s": 2, "address_space_mb": 512, "open_files": 32, "processes": 0, "file_size_mb": 1,
                               "wall_s": 5.0}


def profile_status() -> dict:
    posix = os.name == "posix"
    return {
        "process_separation": True,
        "rlimits": posix,
        "empty_environment": True,
        "isolated_interpreter_flags": True,
        "network_namespace": False,
        "filesystem_namespace": False,
        "syscall_filter": False,
        "wasm_runtime": False,
        "microvm": False,
        "adversarial_production_ready": False,
    }


def _preexec(limits: dict):
    def apply():  # runs in the child before exec (POSIX only)
        import resource
        mb = 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CPU, (limits["cpu_s"], limits["cpu_s"]))
        resource.setrlimit(resource.RLIMIT_AS, (limits["address_space_mb"] * mb,) * 2)
        resource.setrlimit(resource.RLIMIT_NOFILE, (limits["open_files"],) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (limits["file_size_mb"] * mb,) * 2)
        if hasattr(resource, "RLIMIT_NPROC") and os.getuid() != 0:
            resource.setrlimit(resource.RLIMIT_NPROC, (limits["processes"],) * 2)
        os.setsid()
    return apply


def run_isolated(code: str, *, stdin: str = "", limits: dict | None = None) -> dict:
    """Run untrusted Python source in a separate constrained process."""
    lim = dict(DEFAULT_LIMITS, **(limits or {}))
    with tempfile.TemporaryDirectory(prefix="inv41-iso-") as cwd:
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-c", code], input=stdin, capture_output=True, text=True,
                cwd=cwd, env={}, close_fds=True, timeout=lim["wall_s"],
                preexec_fn=_preexec(lim) if os.name == "posix" else None,
            )
            return {"terminated": False, "returncode": proc.returncode, "stdout": proc.stdout[-65536:],
                    "stderr": proc.stderr[-65536:]}
        except subprocess.TimeoutExpired:
            return {"terminated": True, "returncode": None, "reason": "wall-clock quota", "stdout": "", "stderr": ""}


class CapabilityBridge:
    """Session-bound opaque handle table across the isolation boundary."""

    def __init__(self) -> None:
        self._sessions: dict = {}
        self._lock = threading.Lock()

    def open_session(self, principal_key: str, holder: Holder) -> str:
        if not isinstance(holder, Holder):
            raise TypeError("holder required")
        sid = secrets.token_urlsafe(24)
        membrane = Membrane(f"bridge-session")
        handles = {}
        for alias, ref in holder.held.items():
            handles[secrets.token_urlsafe(24)] = (alias, membrane.wrap(ref))
        with self._lock:
            self._sessions[sid] = {"principal": principal_key, "membrane": membrane, "handles": handles,
                                   "authority": holder._authority_id}
        return sid

    def handles(self, sid: str) -> dict:
        s = self._sessions.get(sid)
        if s is None:
            raise AuthenticationFailed("unknown session")
        return {h: alias for h, (alias, _r) in s["handles"].items()}

    def request(self, sid: str, principal_key: str, message: str) -> str:
        """Process one JSON request {"handle":..., "op":...}; returns JSON.  Never returns a Reference."""
        try:
            s = self._sessions.get(sid)
            if s is None or s["principal"] != principal_key:
                raise AuthenticationFailed("session/principal mismatch")
            if not isinstance(message, str) or len(message) > 4096:
                raise ValueError("message too large")
            req = json.loads(message)
            if not isinstance(req, dict) or set(req) != {"handle", "op"}:
                raise ValueError("malformed request")
            entry = s["handles"].get(req["handle"])
            if entry is None:
                raise AuthenticationFailed("unknown handle")
            _alias, ref = entry
            result = ref.invoke(req["op"])
            return json.dumps({"ok": True, "result": result})
        except (CapabilityError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return json.dumps({"ok": False, "error": describe(exc)})

    def close_session(self, sid: str) -> dict:
        with self._lock:
            s = self._sessions.pop(sid, None)
        if s is None:
            return {"closed": False}
        return {"closed": True, **s["membrane"].revoke()}
