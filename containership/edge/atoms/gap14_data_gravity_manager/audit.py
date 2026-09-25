"""Tamper-evident audit sink (G14-P0-10).

Append-only JSON-lines.  Each record carries ``seq``, ``prev`` (digest of the
previous record) and a MAC from the audit key, so deletion, reordering,
insertion or edits are detected by ``verify_chain``.  A write failure raises
G14_AUDIT_UNAVAILABLE and the decision service withholds the decision
(fail-closed: no unaudited recommendation leaves the service).

Records contain digests/IDs, never secrets; tenant/dataset IDs are kept as
issued because the audit store is access-controlled evidence (see docs/DESIGN.md
§Data classification), while logs/metrics use redacted forms.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Iterable, Mapping

from .errors import G14Error
from .trust import KeyRing, canonical_json, digest

GENESIS = "sha256:" + "0" * 64
RECORD_SCHEMA = "PK_AUDIT_RECORD/1"


class AuditSink:
    def __init__(self, keyring: KeyRing, kid: str):
        self.keyring, self.kid = keyring, kid
        self._lock = threading.Lock()
        self._seq = 0
        self._head = GENESIS

    @property
    def head(self) -> dict[str, Any]:
        return {"seq": self._seq, "head": self._head}

    def _seal(self, event: str, payload: Mapping[str, Any], at: float) -> dict[str, Any]:
        rec = {"schema": RECORD_SCHEMA, "seq": self._seq + 1, "prev": self._head, "event": event, "at": at,
               "payload": dict(payload)}
        rec["mac"] = self.keyring.sign(rec, self.kid)
        return rec

    def append(self, event: str, payload: Mapping[str, Any], at: float) -> dict[str, Any]:
        with self._lock:
            try:
                rec = self._seal(event, payload, at)
            except G14Error as exc:  # signing key unavailable/revoked -> no evidence -> fail closed
                raise G14Error("G14_AUDIT_UNAVAILABLE", "audit signing failed", details={"cause": exc.code}) from None
            try:
                self._write(rec)
            except OSError as exc:
                raise G14Error("G14_AUDIT_UNAVAILABLE", "audit write failed", details={"error": type(exc).__name__}) from None
            self._seq = rec["seq"]
            self._head = digest(rec)
            return {"seq": rec["seq"], "digest": self._head}

    def _write(self, rec: Mapping[str, Any]) -> None:
        raise NotImplementedError


class MemoryAuditSink(AuditSink):
    def __init__(self, keyring: KeyRing, kid: str, *, fail: bool = False):
        super().__init__(keyring, kid)
        self.records: list[dict[str, Any]] = []
        self.fail = fail

    def _write(self, rec: Mapping[str, Any]) -> None:
        if self.fail:
            raise OSError("injected audit failure")
        self.records.append(json.loads(json.dumps(rec)))


class FileAuditSink(AuditSink):
    """fsync'd JSONL file; resumes the chain head from an existing file."""

    def __init__(self, keyring: KeyRing, kid: str, path: str | os.PathLike[str]):
        super().__init__(keyring, kid)
        self.path = Path(path)
        if self.path.exists():
            recs = list(read_records(self.path))
            verify_chain(recs, keyring)
            if recs:
                self._seq, self._head = recs[-1]["seq"], digest(recs[-1])

    def _write(self, rec: Mapping[str, Any]) -> None:
        line = canonical_json(rec) + b"\n"
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line)
            os.fsync(fd)
        finally:
            os.close(fd)


def read_records(path: str | os.PathLike[str]) -> Iterable[dict[str, Any]]:
    with open(path, "rb") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    raise G14Error("G14_AUDIT_CHAIN_BROKEN", f"unparseable audit line {n}") from None


def verify_chain(records: Iterable[Mapping[str, Any]], keyring: KeyRing, *, start_head: str = GENESIS,
                 start_seq: int = 0) -> dict[str, Any]:
    prev, seq, count = start_head, start_seq, 0
    for rec in records:
        body = {k: v for k, v in rec.items() if k != "mac"}
        if rec.get("seq") != seq + 1 or rec.get("prev") != prev:
            raise G14Error("G14_AUDIT_CHAIN_BROKEN", "sequence/link break", details={"at_seq": rec.get("seq"), "expected": seq + 1})
        try:
            keyring.verify(body, rec.get("mac", {}), expected_issuer=None, now=float(rec.get("at", 0)))
        except G14Error:
            raise G14Error("G14_AUDIT_CHAIN_BROKEN", "record MAC invalid", details={"at_seq": rec.get("seq")}) from None
        prev, seq, count = digest(rec), rec["seq"], count + 1
    return {"records": count, "head": prev, "seq": seq}
