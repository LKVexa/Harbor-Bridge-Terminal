"""Tamper-evident security audit chain (Section 13, REQ-AUD-*).

Events are canonical JSON, hash-chained (each event commits to the previous
event's digest and a strictly increasing sequence number) and every event is
HMAC-sealed with an audit-sealing key that is separate from any capability
seal.  ``verify_chain`` is an offline verifier: it detects modified, deleted,
duplicated, reordered and truncated events (truncation needs the externally
recorded head digest).  Secret material is refused at emit time, not scrubbed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import time
import uuid
from collections import deque
from typing import Callable, Final, Iterable

AUDIT_SCHEMA: Final[str] = "INV41_AUDIT_EVENT/1"
GENESIS: Final[str] = "0" * 64

EVENT_TYPES: Final[frozenset] = frozenset({
    "authority.created", "policy.loaded", "grant", "bind", "attenuate", "wrap", "revoke",
    "use.allowed", "use.denied", "reference.invalid", "cross_authority.attempt",
    "config.activated", "config.rejected", "config.rollback", "auth.failure", "auth.success",
    "release_gate.override", "chain.segment_start", "quarantine",
})
SEVERITY: Final[dict] = {
    "cross_authority.attempt": "critical", "reference.invalid": "high", "use.denied": "medium",
    "auth.failure": "high", "config.rejected": "high", "config.rollback": "high",
    "release_gate.override": "critical", "quarantine": "critical",
}
FORBIDDEN_KEYS: Final[frozenset] = frozenset({"seal", "token", "signature", "secret", "key", "password", "credential"})
# Public content digests (not secrets) that may legitimately look like hex tokens.
PUBLIC_DIGEST_KEYS: Final[frozenset] = frozenset({"previous_segment_head", "config_digest", "artifact_digest"})
_TOKENLIKE = re.compile(r"^[A-Za-z0-9_\-]{40,}$|^[0-9a-f]{64}$")


class AuditRejected(ValueError):
    pass


class AuditUnavailable(RuntimeError):
    pass


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _check_safe(fields: dict) -> None:
    for k, v in fields.items():
        if k.lower() in FORBIDDEN_KEYS:
            raise AuditRejected(f"field {k!r} is forbidden in audit events")
        if isinstance(v, str) and k not in PUBLIC_DIGEST_KEYS and _TOKENLIKE.match(v):
            raise AuditRejected(f"field {k!r} looks like secret/token material")
        if isinstance(v, dict):
            _check_safe(v)


class AuditChain:
    """Append-only, bounded, hash-chained and HMAC-sealed audit log.

    ``mandatory=True`` means a critical action must not proceed if the event
    cannot be recorded (buffer full and sink failing): ``emit`` raises
    :class:`AuditUnavailable` and callers deny the action.
    """

    def __init__(self, sealing_key: bytes, *, component_version: str = "4.3.0", max_buffer: int = 10_000,
                 sink: Callable[[dict], None] | None = None, mandatory: bool = True,
                 previous_head: str | None = None) -> None:
        if not isinstance(sealing_key, bytes) or len(sealing_key) < 32:
            raise ValueError("audit sealing key must be >= 32 bytes")
        self._key = sealing_key
        self._version = component_version
        self._buffer: deque = deque()
        self._max = max_buffer
        self._sink = sink
        self._mandatory = mandatory
        self._lock = threading.Lock()
        self._seq = 0
        self._head = GENESIS
        self._segment = uuid.uuid4().hex
        self.dropped = 0
        self.exported: list[dict] = []
        self._append("chain.segment_start", {"previous_segment_head": previous_head or GENESIS}, "success", "SEGMENT")

    @property
    def head(self) -> str:
        return self._head

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    def _append(self, event_type: str, fields: dict, outcome: str, reason: str, correlation_id: str | None = None) -> dict:
        if event_type not in EVENT_TYPES:
            raise AuditRejected(f"unknown event type {event_type!r}")
        _check_safe(fields)
        with self._lock:
            if len(self._buffer) >= self._max:
                self._flush_locked()
                if len(self._buffer) >= self._max:
                    self.dropped += 1
                    raise AuditUnavailable("audit buffer full and sink unavailable")
            self._seq += 1
            body = {
                "schema": AUDIT_SCHEMA, "seq": self._seq, "segment": self._segment, "prev": self._head,
                "type": event_type, "severity": SEVERITY.get(event_type, "info"),
                "wall_time": round(time.time(), 6), "mono_ns": time.monotonic_ns(),
                "component_version": self._version, "outcome": outcome, "reason": reason,
                "correlation_id": correlation_id or uuid.uuid4().hex, "fields": fields,
            }
            digest = hashlib.sha256(canonical(body)).hexdigest()
            event = dict(body, digest=digest, mac=hmac.new(self._key, digest.encode(), hashlib.sha256).hexdigest())
            self._head = digest
            self._buffer.append(event)
            self._flush_locked()
            return event

    def emit(self, event_type: str, *, outcome: str, reason: str, correlation_id: str | None = None, **fields) -> dict:
        try:
            return self._append(event_type, fields, outcome, reason, correlation_id)
        except AuditUnavailable:
            if self._mandatory:
                raise
            return {}

    def _flush_locked(self) -> None:
        while self._buffer:
            event = self._buffer[0]
            if self._sink is not None:
                try:
                    self._sink(event)
                except Exception:
                    return  # keep buffered; never drop silently
            self.exported.append(event)
            self._buffer.popleft()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()


def verify_chain(events: Iterable[dict], sealing_key: bytes, *, expected_head: str | None = None,
                 expected_count: int | None = None) -> dict:
    """Offline verifier.  Returns {"valid": bool, "errors": [...], "events": n, "head": digest}."""
    errors: list[str] = []
    prev = None
    last_seq = 0
    last_mono = None
    segment = None
    n = 0
    head = GENESIS
    for n, event in enumerate(events, 1):
        body = {k: v for k, v in event.items() if k not in ("digest", "mac")}
        if body.get("schema") != AUDIT_SCHEMA:
            errors.append(f"#{n}: bad schema")
        if body.get("type") not in EVENT_TYPES:
            errors.append(f"#{n}: unknown type")
        digest = hashlib.sha256(canonical(body)).hexdigest()
        if digest != event.get("digest"):
            errors.append(f"#{n}: digest mismatch (modified)")
        mac = hmac.new(sealing_key, str(event.get("digest")).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, str(event.get("mac"))):
            errors.append(f"#{n}: seal mismatch")
        if segment is None:
            segment = body.get("segment")
            if body.get("type") != "chain.segment_start" or body.get("prev") != GENESIS:
                errors.append(f"#{n}: chain does not start at a segment anchor")
        elif body.get("segment") != segment:
            errors.append(f"#{n}: segment changed mid-chain")
        if prev is not None and body.get("prev") != prev:
            errors.append(f"#{n}: prev link broken (deleted/reordered)")
        seq = body.get("seq", 0)
        if seq != last_seq + 1:
            errors.append(f"#{n}: sequence discontinuity {last_seq}->{seq}")
        mono = body.get("mono_ns")
        if last_mono is not None and isinstance(mono, int) and mono < last_mono:
            errors.append(f"#{n}: monotonic clock went backwards")
        last_mono = mono
        last_seq = seq
        prev = event.get("digest")
        head = prev
    if expected_head is not None and head != expected_head:
        errors.append("head mismatch (truncated or extended)")
    if expected_count is not None and n != expected_count:
        errors.append(f"count mismatch {n} != {expected_count}")
    return {"valid": not errors, "errors": errors, "events": n, "head": head}
