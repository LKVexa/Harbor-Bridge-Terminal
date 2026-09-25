"""Backend adapter boundary (MC-004, MC-005, MC-007) and external runtime pins (MC-001).

The service talks to storage only through :class:`BackendAdapter`, which is
independent of any backend SDK (MC-005-01).  Two adapters ship:

* :class:`LocalBackend` -- the in-package MVCC engine + WAL (single member).
  This is the only backend the package can *prove* today.
* :class:`ExternalBackendContract` -- the fail-closed boundary for an approved
  consensus-backed production backend (for example an etcd v3 cluster).  It
  validates the pin file ``deploy/backend_pin.json`` and **refuses to start**
  until the owner has selected and pinned a backend release + digest
  (MC-004-01/05).  No SDK is vendored and no behaviour is simulated, so no
  false evidence is produced.

Error classification (MC-005-04) is centralised in :func:`classify_backend_error`.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from typing import Any, Protocol

from .errors import (
    CompactedError, DeadlineExceeded, FailedClosed, InvalidArgument, Overloaded, PermissionDenied,
    StateError, Unauthenticated, Unavailable,
)
from .store import ControlStore

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_PIN_PATH = os.path.join(HERE, "deploy", "backend_pin.json")
PKCORE_PIN_PATH = os.path.join(HERE, "deploy", "pk_core_pin.json")
SUPPORTED_PYTHON = ((3, 10), (3, 13))


class BackendAdapter(Protocol):
    name: str

    def identity(self) -> dict[str, Any]: ...
    def healthy(self) -> bool: ...
    def store(self) -> ControlStore: ...


class LocalBackend:
    name = "inv05-local-mvcc"

    def __init__(self, store: ControlStore, version: str = "1") -> None:
        self._store, self.version = store, version

    def identity(self) -> dict[str, Any]:
        return {"backend": self.name, "version": self.version, "members": 1, "quorum": "single-member",
                "consensus": "none (single writer; see ADR-002)"}

    def healthy(self) -> bool:
        return not self._store.failed

    def store(self) -> ControlStore:
        return self._store


def load_pin(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class ExternalBackendContract:
    """Fail-closed placeholder for the owner-approved distributed backend."""

    REQUIRED_FEATURES = ("linearizable_txn", "mvcc_revisions", "watch_from_revision", "compaction_error",
                         "leases_with_ttl", "member_add_remove_joint", "mtls_peer_and_client", "snapshot_restore")

    def __init__(self, pin_path: str = BACKEND_PIN_PATH) -> None:
        self.pin = load_pin(pin_path)
        self.name = self.pin.get("backend") or "unselected"

    def preflight(self) -> list[str]:
        p = self.pin
        problems = []
        if p.get("status") != "APPROVED":
            problems.append(f"backend pin status is {p.get('status')!r}, not APPROVED (owner decision pending)")
        for f in ("backend", "version", "artifact_sha256", "approved_by", "approved_on"):
            if not p.get(f):
                problems.append(f"backend pin missing {f}")
        missing = [f for f in self.REQUIRED_FEATURES if f not in p.get("features", [])]
        if missing:
            problems.append(f"backend pin lacks required features {missing}")
        return problems

    def verify_artifact(self, artifact_path: str) -> bool:
        """MC-004-05: verify the downloaded backend binary against the pinned digest."""
        h = hashlib.sha256()
        with open(artifact_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest() == self.pin.get("artifact_sha256")

    def connect(self) -> None:
        problems = self.preflight()
        if problems:
            raise Unavailable("production backend not approved/pinned: " + "; ".join(problems),
                              dependency="backend")
        raise Unavailable("no SDK adapter is bundled for the pinned backend; implement against this contract",
                          dependency="backend")


def classify_backend_error(exc: BaseException) -> StateError:
    """Map transport/backend exceptions to canonical error classes (MC-005-04)."""
    if isinstance(exc, StateError):
        return exc
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if isinstance(exc, TimeoutError) or "deadline" in msg or "timeout" in name:
        return DeadlineExceeded("backend deadline exceeded", dependency="backend")
    if isinstance(exc, (ConnectionError, OSError)) and not isinstance(exc, PermissionError):
        return Unavailable("backend unreachable", dependency="backend")
    if isinstance(exc, PermissionError) or "permission" in msg:
        return PermissionDenied("backend denied access", dependency="backend")
    if "unauthenticated" in msg or "certificate" in msg:
        return Unauthenticated("backend authentication failed", dependency="backend")
    if "compacted" in msg:
        return CompactedError("backend revision compacted", dependency="backend")
    if "too many requests" in msg or "overload" in msg:
        return Overloaded("backend overloaded", dependency="backend", retry_after_s=0.5)
    if "corrupt" in msg:
        return FailedClosed("backend reported corruption", dependency="backend")
    if isinstance(exc, (ValueError, TypeError)):
        return InvalidArgument("backend rejected request", dependency="backend")
    return Unavailable("backend error", dependency="backend")


def runtime_self_test(require_pk_core: bool = False) -> dict[str, Any]:
    """Startup self-test (MC-001-05): interpreter range + pk_core presence/version."""
    report: dict[str, Any] = {"python": ".".join(map(str, sys.version_info[:3])), "problems": []}
    lo, hi = SUPPORTED_PYTHON
    if not (lo <= sys.version_info[:2] <= hi):
        report["problems"].append(f"python {report['python']} outside supported {lo}..{hi}")
    pin = load_pin(PKCORE_PIN_PATH) if os.path.exists(PKCORE_PIN_PATH) else {}
    report["pk_core_pin"] = {k: pin.get(k) for k in ("version", "artifact_sha256", "status")}
    extra = os.environ.get("PK_CORE_PATH")
    if extra and extra not in sys.path:
        sys.path.insert(0, extra)
    try:
        mod = importlib.import_module("pk_core")
        ver = getattr(mod, "__version__", "unknown")
        report["pk_core"] = ver
        if pin.get("version") and ver != pin["version"]:
            report["problems"].append(f"pk_core {ver} does not match pinned {pin['version']}")
    except ImportError:
        report["pk_core"] = None
        if require_pk_core:
            report["problems"].append("pk_core not importable (required for the 100-item framework gate)")
    report["ok"] = not report["problems"]
    return report
