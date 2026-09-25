"""Persistent tamper-evident audit export and anchoring (v6).

* ``AuditExporter`` pulls batches from a local ``AuditLedger``, verifies chain
  continuity (sequence + previous-hash) against the last exported head,
  applies redaction, and appends to a ``Sink``.  Collector outages spool to a
  bounded, integrity-protected local spool; when the spool is full the
  exporter reports ``AUDIT_SPOOL_FULL`` so callers can block security
  operations instead of dropping events.
* ``AppendOnlyFileSink`` - append-only JSONL (O_APPEND) that refuses any batch
  that does not extend its current head: rewriting/reordering/duplication is
  impossible through the sink API.  Production deployments back this with
  WORM/object-lock storage (see deploy/ and RUNBOOKS.md); that storage
  integration is estate-side.
* Periodic anchoring appends the current chain head into an independent
  transparency log and stores the inclusion evidence.
* ``verify_export`` is the independent verifier: recomputes every event hash,
  checks continuity/gaps and each anchor's inclusion proof.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Mapping, Protocol, Sequence

from .canonical import canonical_bytes
from .core import AUDIT_SCHEMA, AuditLedger
from .errors import fail
from .telemetry import redact
from .tlog import LocalTransparencyLog, LogKey, verify_inclusion_evidence

ANCHOR_SCHEMA = "PK_AUDIT_ANCHOR/1"


def _event_hash(rec: Mapping[str, Any]) -> str:
    body = {k: rec.get(k) for k in ("schema", "sequence", "event", "time", "details", "previous")}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


class Sink(Protocol):
    def head(self) -> tuple[int, str | None]: ...
    def append_batch(self, events: Sequence[Mapping[str, Any]]) -> None: ...


class AppendOnlyFileSink:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._next, self._head = 0, None
        self.available = True
        if os.path.exists(path):
            res = verify_export(path)
            self._next, self._head = res["events"], res["head"]

    def head(self) -> tuple[int, str | None]:
        return self._next, self._head

    def append_batch(self, events: Sequence[Mapping[str, Any]]) -> None:
        if not self.available:
            raise ConnectionError("collector unavailable")
        with self._lock:
            seq, head = self._next, self._head
            lines = []
            for e in events:
                if e.get("type") == "anchor":
                    lines.append(canonical_bytes(e))
                    continue
                if e["sequence"] != seq or e["previous"] != head or _event_hash(e) != e["hash"]:
                    raise fail("AUDIT_CHAIN_BROKEN", "batch does not extend exported chain", expected_sequence=seq)
                seq, head = seq + 1, e["hash"]
                lines.append(canonical_bytes(dict(e)))
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
            try:
                os.write(fd, b"".join(line + b"\n" for line in lines))
                os.fsync(fd)
            finally:
                os.close(fd)
            self._next, self._head = seq, head


class AuditExporter:
    def __init__(self, ledger: AuditLedger, sink: Sink, *, spool_limit: int = 10_000, anchor_log: LocalTransparencyLog | None = None,
                 anchor_every: int = 100):
        self._ledger = ledger
        self._sink = sink
        self._spool: list[dict[str, Any]] = []
        self._limit = spool_limit
        self._log = anchor_log
        self._every = anchor_every
        self._since_anchor = 0
        self.healthy = True
        self.last_error: str | None = None

    def pending(self) -> int:
        return len(self._ledger.events) - self._sink.head()[0] if not self._spool else len(self._spool)

    def export(self, *, now: int) -> dict[str, Any]:
        if not self._ledger.verify():
            self.healthy = False
            raise fail("AUDIT_CHAIN_BROKEN", "local audit ledger failed verification before export")
        start, head = self._sink.head() if not self._spool else (self._spool[-1]["sequence"] + 1, self._spool[-1]["hash"])
        new = [redact(dict(e)) | {"details": redact(e["details"])} for e in self._ledger.events[start:]]
        if new and new[0]["previous"] != head:
            self.healthy = False
            raise fail("AUDIT_CHAIN_BROKEN", "local ledger does not continue exported chain (gap/rewrite)")
        for e in new:  # redaction must not change hashes: only non-hashed secrets may be redacted
            if _event_hash(e) != e["hash"]:
                self.healthy = False
                raise fail("AUDIT_CHAIN_BROKEN", "event contains secret-like material; refusing to export altered chain", sequence=e["sequence"])
        batch = self._spool + new
        if self._log is not None and batch and self._since_anchor + len(new) >= self._every:
            anchor_head = batch[-1]["hash"]
            idx = self._log.append(canonical_bytes({"schema": ANCHOR_SCHEMA, "head": anchor_head, "sequence": batch[-1]["sequence"]}))
            cp = self._log.checkpoint(now)
            batch = batch + [{"type": "anchor", "schema": ANCHOR_SCHEMA, "head": anchor_head, "sequence": batch[-1]["sequence"],
                              "evidence": {"index": idx, "checkpoint": cp, "proof": self._log.prove_inclusion(idx, cp["size"])}}]
            self._since_anchor = 0
        try:
            if batch:
                self._sink.append_batch(batch)
            self._spool = []
            self._since_anchor += len(new)
            self.healthy, self.last_error = True, None
            return {"exported": len(new), "spooled": 0}
        except (ConnectionError, OSError, TimeoutError) as exc:
            events_only = [e for e in batch if e.get("type") != "anchor"]
            if len(events_only) > self._limit:
                self.healthy = False
                self.last_error = "AUDIT_SPOOL_FULL"
                raise fail("AUDIT_SPOOL_FULL", "audit collector down and spool exhausted", spooled=len(events_only)) from exc
            self._spool = events_only
            self.healthy, self.last_error = False, type(exc).__name__
            return {"exported": 0, "spooled": len(self._spool)}


def verify_export(path: str, *, log_keys: Mapping[str, LogKey] | None = None, now: int | None = None,
                  max_anchor_age_s: int = 10**9, expected_head: str | None = None, min_events: int | None = None,
                  require_anchored: bool = False) -> dict[str, Any]:
    """Independent verifier for an exported audit file.

    Truncation is only detectable against an external reference: pass
    ``expected_head``/``min_events`` (e.g. from the latest verified anchor in
    the independent log) and/or ``require_anchored`` to refuse an unanchored
    tail.  The result always reports ``unanchored_tail``.
    """
    seq, head, anchors, anchored_seq = 0, None, 0, -1
    with open(path, "rb") as fh:
        for n, line in enumerate(fh):
            rec = json.loads(line)
            if rec.get("type") == "anchor":
                if rec["head"] != head:
                    raise fail("AUDIT_CHAIN_BROKEN", "anchor does not match chain head at its position", line=n)
                if log_keys is not None:
                    entry = canonical_bytes({"schema": ANCHOR_SCHEMA, "head": rec["head"], "sequence": rec["sequence"]})
                    verify_inclusion_evidence(rec["evidence"], entry=entry, log_keys=log_keys, now=now or rec["evidence"]["checkpoint"]["timestamp"],
                                              max_checkpoint_age_s=max_anchor_age_s)
                anchors += 1
                anchored_seq = rec["sequence"]
                continue
            if rec.get("schema") != AUDIT_SCHEMA or rec.get("sequence") != seq or rec.get("previous") != head:
                raise fail("AUDIT_CHAIN_BROKEN", "gap, reorder or foreign record in exported audit chain", line=n, expected_sequence=seq)
            if _event_hash(rec) != rec.get("hash"):
                raise fail("AUDIT_CHAIN_BROKEN", "event hash mismatch (tampered)", line=n)
            seq, head = seq + 1, rec["hash"]
            if expected_head is not None and rec["hash"] == expected_head:
                expected_head = None  # reached
    tail = seq - (anchored_seq + 1)
    if expected_head is not None:
        raise fail("AUDIT_CHAIN_BROKEN", "export does not contain the expected head (truncated or forked)")
    if min_events is not None and seq < min_events:
        raise fail("AUDIT_CHAIN_BROKEN", "export has fewer events than the external reference (truncated)", events=seq, expected=min_events)
    if require_anchored and tail > 0:
        raise fail("AUDIT_CHAIN_BROKEN", "export ends in an unanchored tail", unanchored_tail=tail)
    return {"verified": True, "events": seq, "head": head, "anchors": anchors, "unanchored_tail": tail}
