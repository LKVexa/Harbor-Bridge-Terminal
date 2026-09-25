"""MC-22 - Tamper-evident security audit event ledger.

Append-only JSON-lines file. Each record carries ``seq``, ``prev`` (SHA-256 of
the previous record line), the event, and an HMAC over the record using an
``audit``-purpose key from the ``KeyRing``. ``verify()`` recomputes the chain
and the MACs; truncation is detected against an externally anchored head
(``expected_head``/``expected_seq``).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import threading
import time
from typing import Any, Mapping

from .errors import PlaneError
from .secret_refs import redact
from .trust import KeyRing, canonical

GENESIS = "0" * 64
EVENT_FIELDS = {"action", "outcome", "actor", "tenant", "correlation_id", "resource", "reason"}
ACTIONS = {"resolve", "publish", "quarantine", "release", "freeze", "unfreeze", "disable", "enable",
           "config_activate", "config_rollback", "authn_failure", "authz_denied", "key_rotate", "catalogue_accept",
           "catalogue_reject"}


class AuditLedger:
    def __init__(self, path: str | os.PathLike, ring: KeyRing, key_id: str, clock=time.time) -> None:
        self.path = pathlib.Path(path)
        self.ring, self.key_id, self._clock = ring, key_id, clock
        self._lock = threading.Lock()
        self._seq, self._head = self._recover()

    def _recover(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        info = verify(self.path, self.ring)
        return info["seq"], info["head"]

    def append(self, event: Mapping[str, Any]) -> dict:
        if not isinstance(event, Mapping) or not set(event) <= EVENT_FIELDS or "action" not in event:
            raise PlaneError("malformed audit event", code="INVALID_APPLICATION", details={"field": "event"})
        if event["action"] not in ACTIONS:
            raise PlaneError("unknown audit action", code="INVALID_APPLICATION", details={"field": "action"})
        safe = redact({k: (str(v)[:256] if v is not None else None) for k, v in event.items()})
        with self._lock:
            rec = {"seq": self._seq + 1, "ts": round(self._clock(), 3), "prev": self._head, "event": safe,
                   "kid": self.key_id}
            rec["mac"] = self.ring.sign(self.key_id, "audit", rec)
            line = canonical(rec)
            with open(self.path, "ab") as fh:
                fh.write(line + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._seq, self._head = rec["seq"], hashlib.sha256(line).hexdigest()
            return rec

    @property
    def head(self) -> tuple[int, str]:
        return self._seq, self._head

    def export(self, tenant: str | None = None) -> list[dict]:
        out = []
        with open(self.path, "rb") as fh:
            for line in fh:
                rec = json.loads(line)
                if tenant is None or rec["event"].get("tenant") == tenant:
                    out.append(rec)
        return out


def verify(path: str | os.PathLike, ring: KeyRing, *, expected_head: str | None = None,
           expected_seq: int | None = None) -> dict:
    head, seq = GENESIS, 0
    p = pathlib.Path(path)
    if p.exists():
        with open(p, "rb") as fh:
            for raw in fh:
                line = raw.rstrip(b"\n")
                try:
                    rec = json.loads(line)
                    mac = rec.pop("mac")
                except Exception:
                    raise PlaneError("audit record unreadable", code="AUDIT_CHAIN_BROKEN", details={"sequence": seq + 1}) from None
                if rec.get("seq") != seq + 1 or rec.get("prev") != head:
                    raise PlaneError("audit chain broken", code="AUDIT_CHAIN_BROKEN", details={"sequence": seq + 1})
                try:
                    ring.verify(rec["kid"], "audit", rec, mac)
                except PlaneError:
                    raise PlaneError("audit MAC invalid", code="AUDIT_CHAIN_BROKEN", details={"sequence": seq + 1}) from None
                rec["mac"] = mac
                if canonical(rec) != line:
                    raise PlaneError("audit record not canonical", code="AUDIT_CHAIN_BROKEN", details={"sequence": seq + 1})
                seq, head = rec["seq"], hashlib.sha256(line).hexdigest()
    if expected_seq is not None and seq < expected_seq:
        raise PlaneError("audit ledger truncated", code="AUDIT_CHAIN_BROKEN", details={"sequence": seq})
    if expected_head is not None and expected_seq == seq and head != expected_head:
        raise PlaneError("audit head mismatch", code="AUDIT_CHAIN_BROKEN", details={"sequence": seq})
    return {"seq": seq, "head": head}
