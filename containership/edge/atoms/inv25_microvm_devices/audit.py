"""PK_DEVICE_AUDIT_EVENT/1 - hash-chained, tamper-evident audit log for INV-25."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import threading
import uuid
from typing import Any, Iterable

from .errors import Inv25Error
from .model import canonical_json

SCHEMA = "PK_DEVICE_AUDIT_EVENT/1"
GENESIS = "sha256:" + "0" * 64
EVENT_TYPES = frozenset({
    "registration.accepted", "registration.rejected", "replacement.accepted", "replacement.rejected",
    "surface.widened", "surface.reduced", "forbidden_class.attempt", "authn.failure", "authz.denied",
    "artifact.verification_failed", "artifact.verified", "config.activated", "config.activation_failed",
    "config.rolled_back", "emergency.disable", "emergency.restore", "gate.waiver_approved",
})
SECURITY_SENSITIVE = frozenset({
    "surface.widened", "forbidden_class.attempt", "authn.failure", "authz.denied",
    "artifact.verification_failed", "emergency.disable", "gate.waiver_approved", "config.rolled_back",
})
_FORBIDDEN_KEYS = ("token", "secret", "password", "credential", "key_material")


class AuditUnavailable(Inv25Error):
    code = "INV25_AUDIT_UNAVAILABLE"


class AuditTampered(Inv25Error):
    code = "INV25_ARTIFACT_VERIFICATION_FAILED"


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _event_digest(ev: dict[str, Any]) -> str:
    body = {k: v for k, v in ev.items() if k != "digest"}
    return "sha256:" + hashlib.sha256(canonical_json(body)).hexdigest()


class AuditLog:
    """Append-only hash chain. Optional JSONL file sink (opened O_APPEND)."""

    def __init__(self, path: str | os.PathLike | None = None, *, fail: bool = False) -> None:
        self.events: list[dict[str, Any]] = []
        self.path = os.fspath(path) if path else None
        self._lock = threading.Lock()
        self.fail = fail  # fault-injection hook: simulate unavailable sink

    @property
    def head(self) -> str:
        return self.events[-1]["digest"] if self.events else GENESIS

    def emit(self, event_type: str, *, actor: str, result: str, environment: str = "",
             device: str = "", correlation_id: str = "", **fields: Any) -> dict[str, Any]:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown audit event type {event_type}")
        for k in fields:
            if any(f in k.lower() for f in _FORBIDDEN_KEYS):
                raise ValueError(f"audit field {k!r} may not carry secrets")
        with self._lock:
            if self.fail:
                raise AuditUnavailable("audit sink unavailable")
            ev = {
                "schema": SCHEMA, "event_id": str(uuid.uuid4()), "event_type": event_type,
                "security_sensitive": event_type in SECURITY_SENSITIVE, "timestamp": utcnow(),
                "actor": actor, "environment": environment, "device": device, "result": result,
                "correlation_id": correlation_id, "prev": self.head, **fields,
            }
            ev["digest"] = _event_digest(ev)
            if self.path:
                try:
                    fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
                    with os.fdopen(fd, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(ev, sort_keys=True) + "\n")
                except OSError as exc:
                    raise AuditUnavailable("audit sink write failed") from exc
            self.events.append(ev)
            return ev

    @staticmethod
    def verify_chain(events: Iterable[dict[str, Any]]) -> int:
        """Return the number of verified events; raise AuditTampered on any break."""
        prev, n = GENESIS, 0
        for ev in events:
            if ev.get("prev") != prev or _event_digest(ev) != ev.get("digest"):
                raise AuditTampered(f"audit chain broken at event {n}")
            prev, n = ev["digest"], n + 1
        return n

    @classmethod
    def verify_file(cls, path: str | os.PathLike) -> int:
        with open(path, encoding="utf-8") as fh:
            return cls.verify_chain(json.loads(line) for line in fh if line.strip())
