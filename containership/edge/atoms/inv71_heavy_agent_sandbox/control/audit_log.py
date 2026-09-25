"""Durable, signed, hash-chained security audit stream (C049, C073-IMP-04, C067-IMP-02).

* Append-only JSONL file, fsync'd per record (write ordering: a record is on
  disk before the caller is told the action happened).
* Each record carries the previous record hash; every ``checkpoint_every``
  records a signed checkpoint is emitted and handed to an external anchor
  callable (off-node WORM sink in production; a list in tests).
* ``verify_file`` detects deletion, insertion, mutation, reordering, duplicate
  sequence, broken MAC, and checkpoint discontinuity - and, given the external
  anchors, tail truncation.
* When the spool is full the stream refuses (``AUDIT.SINK_UNAVAILABLE``) rather
  than dropping security events; callers must fail the guarded action.

HMAC keys are a reference stand-in for node signing keys held in a KMS/HSM.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Any, Callable

from .config import canonical_bytes
from .errors import ControlError

ZERO = "0" * 64
REQUIRED = ("seq", "ts", "clock", "node", "actor", "operation", "outcome", "reason",
            "tenant", "session", "correlation_id", "config_digest", "policy_version", "prev")
SECRET_KEYS = frozenset({"token", "secret", "password", "authorization", "key", "credential", "cookie"})


def _mac(key: bytes, body: dict) -> str:
    return hmac.new(key, canonical_bytes(body), hashlib.sha256).hexdigest()


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    """Allowlist-style: drop any field whose name marks it as secret material."""
    return {k: ("[REDACTED]" if any(s in k.lower() for s in SECRET_KEYS) else v) for k, v in fields.items()}


class AuditStream:
    def __init__(self, path: Path, *, key: bytes, node: str, clock: Callable[[], float],
                 anchor: Callable[[dict], None], checkpoint_every: int = 64,
                 max_spool_bytes: int = 64 << 20, fsync: bool = True) -> None:
        self.path, self._key, self.node, self._clock = Path(path), key, node, clock
        self._anchor, self.every, self.max_bytes, self._fsync = anchor, checkpoint_every, max_spool_bytes, fsync
        self._lock = threading.Lock()
        self.seq, self.head = 0, ZERO
        self.anchor_failures = 0
        if self.path.exists():
            ok, info = verify_file(self.path, key=key)
            if not ok:
                raise ControlError("AUDIT.SINK_UNAVAILABLE", f"existing stream fails verification: {info}")
            self.seq, self.head = info["last_seq"], info["head"]

    def append(self, *, actor: str, operation: str, outcome: str, reason: str, tenant: str = "",
               session: str = "", correlation_id: str = "", config_digest: str = "",
               policy_version: str = "", **extra: Any) -> dict:
        with self._lock:
            body = {"kind": "event", "seq": self.seq + 1, "ts": self._clock(), "clock": "injected-monotonic",
                    "node": self.node, "actor": actor, "operation": operation, "outcome": outcome,
                    "reason": reason, "tenant": tenant, "session": session, "correlation_id": correlation_id,
                    "config_digest": config_digest, "policy_version": policy_version, "prev": self.head,
                    "extra": redact(extra)}
            rec = dict(body, mac=_mac(self._key, body))
            size = self.path.stat().st_size if self.path.exists() else 0
            if size + len(json.dumps(rec)) + 1 > self.max_bytes:
                raise ControlError("AUDIT.SINK_UNAVAILABLE", "spool full; refusing to drop security events")
            self._write(rec)
            self.seq, self.head = body["seq"], rec["mac"]
            if self.seq % self.every == 0:
                self._checkpoint()
            return rec

    def _write(self, rec: dict) -> None:
        line = json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            if self._fsync:
                os.fsync(f.fileno())

    def _checkpoint(self) -> None:
        body = {"kind": "checkpoint", "seq": self.seq, "head": self.head, "node": self.node, "ts": self._clock()}
        cp = dict(body, mac=_mac(self._key, body))
        self._write_cp(cp)
        try:
            self._anchor(cp)
        except Exception:
            self.anchor_failures += 1  # surfaced by health; the local record still exists

    def _write_cp(self, cp: dict) -> None:
        self._write(cp)

    def checkpoint_now(self) -> None:
        with self._lock:
            self._checkpoint()


def verify_file(path: Path, *, key: bytes, anchors: list[dict] | None = None) -> tuple[bool, dict]:
    prev, expect, last_cp = ZERO, 1, 0
    heads: dict[int, str] = {0: ZERO}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return False, {"error": f"unreadable: {exc}"}
    for n, line in enumerate(lines, 1):
        try:
            rec = json.loads(line)
        except ValueError:
            return False, {"error": f"line {n}: not JSON"}
        mac = rec.pop("mac", "")
        if not hmac.compare_digest(mac, _mac(key, rec)):
            return False, {"error": f"line {n}: bad MAC"}
        if rec.get("kind") == "checkpoint":
            if rec["seq"] != expect - 1 or rec["head"] != prev:
                return False, {"error": f"line {n}: checkpoint discontinuity"}
            last_cp = rec["seq"]
            continue
        if any(k not in rec for k in REQUIRED):
            return False, {"error": f"line {n}: missing field"}
        if rec["seq"] != expect:
            return False, {"error": f"line {n}: sequence {rec['seq']} expected {expect}"}
        if rec["prev"] != prev:
            return False, {"error": f"line {n}: chain break"}
        prev, expect = mac, expect + 1
        heads[rec["seq"]] = mac
    last = expect - 1
    if anchors:
        for a in anchors:
            a = dict(a)
            amac = a.pop("mac", "")
            if not hmac.compare_digest(amac, _mac(key, a)):
                return False, {"error": "anchor MAC invalid"}
            if a["seq"] > last:
                return False, {"error": f"truncated: anchor at seq {a['seq']} beyond local tail {last}"}
            if heads.get(a["seq"]) != a["head"]:
                return False, {"error": f"rewritten: local head at seq {a['seq']} differs from anchor"}
    return True, {"last_seq": last, "head": prev, "last_checkpoint": last_cp}
