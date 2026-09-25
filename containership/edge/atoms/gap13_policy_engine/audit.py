"""G13-MC-010 tamper-evident security audit log.

Append-only JSON-lines; each record carries ``seq`` and ``prev`` (hash of the
previous record) and its own ``hash`` over the canonical body, forming a chain.
``verify_chain`` independently detects modification, deletion, reordering,
truncation (against an expected head), duplicate sequence numbers and forks.
Request payload values are never written (G13-MC-025).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping

from .canonical import canonical_bytes, sha256_hex
from .errors import AuditSinkUnavailable

SCHEMA = "PK_POLICY_AUDIT_EVENT/1"
GENESIS = "0" * 64
_SENSITIVE = ("secret", "token", "password", "private", "credential", "signature")


def _redact(d: Mapping[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in d.items():
        if any(s in k.lower() for s in _SENSITIVE):
            out[k] = "[REDACTED]"
        elif isinstance(v, Mapping):
            out[k] = _redact(v)
        else:
            out[k] = v
    return out


class AuditLog:
    """Hash-chained audit log with a bounded in-memory buffer for sink outages."""

    def __init__(self, path: str | Path | None = None, *, buffer_limit: int = 10_000,
                 clock=time.time) -> None:
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._pending: deque = deque()
        self.buffer_limit = buffer_limit
        self.sink_down = False
        self.clock = clock
        self.seq = 0
        self.head = GENESIS
        if self.path is not None and self.path.exists():
            recs = list(read_log(self.path))
            ok, why = verify_chain(recs)
            if not ok:
                raise AuditSinkUnavailable(f"existing audit log fails verification: {why}")
            self._records = recs
            if recs:
                self.seq, self.head = recs[-1]["seq"], recs[-1]["hash"]

    def emit(self, action: str, *, actor: str = "system", target: str = "", result: str = "ok",
             reason: str = "", correlation_id: str | None = None, **fields: Any) -> dict[str, Any]:
        with self._lock:
            body = {
                "schema": SCHEMA,
                "event_id": str(uuid.uuid4()),
                "seq": self.seq + 1,
                "ts_ms": int(self.clock() * 1000),
                "clock": "wall",
                "actor": actor,
                "action": action,
                "target": target,
                "result": result,
                "reason": reason,
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "fields": _redact(fields),
                "prev": self.head,
            }
            body["hash"] = sha256_hex(canonical_bytes(body))
            if self.sink_down:
                if len(self._pending) >= self.buffer_limit:
                    raise AuditSinkUnavailable("audit sink down and buffer full")
                self._pending.append(body)
            else:
                self._flush_pending()
                self._write(body)
            self._records.append(body)
            self.seq, self.head = body["seq"], body["hash"]
            return body

    def _write(self, rec: dict[str, Any]) -> None:
        if self.path is None:
            return
        with open(self.path, "ab") as fh:
            fh.write(canonical_bytes(rec) + b"\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _flush_pending(self) -> None:
        while self._pending:
            self._write(self._pending.popleft())

    def recover(self) -> int:
        with self._lock:
            self.sink_down = False
            n = len(self._pending)
            self._flush_pending()
            return n

    def require_capacity(self) -> None:
        """Privileged actions fail closed when no audit record could be retained."""
        if self.sink_down and len(self._pending) >= self.buffer_limit:
            raise AuditSinkUnavailable("audit sink down and buffer full")

    def records(self, *, tenant: str | None = None) -> list[dict[str, Any]]:
        if tenant is None:
            return list(self._records)
        return [r for r in self._records if r["fields"].get("tenant") == tenant]

    def health(self) -> dict[str, Any]:
        return {"head": self.head, "seq": self.seq, "sink_down": self.sink_down,
                "buffered": len(self._pending), "buffer_limit": self.buffer_limit}

    def export(self) -> dict[str, Any]:
        recs = self.records()
        manifest = {"schema": "PK_POLICY_AUDIT_EXPORT/1", "count": len(recs), "head": self.head,
                    "records_sha256": sha256_hex(b"".join(canonical_bytes(r) for r in recs))}
        return {"manifest": manifest, "records": recs}


def read_log(path: str | Path) -> Iterable[dict[str, Any]]:
    with open(path, "rb") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def verify_chain(records: list[dict[str, Any]], *, expected_head: str | None = None,
                 expected_count: int | None = None) -> tuple[bool, str]:
    prev, seq = GENESIS, 0
    for i, r in enumerate(records):
        body = {k: v for k, v in r.items() if k != "hash"}
        if sha256_hex(canonical_bytes(body)) != r.get("hash"):
            return False, f"record {i}: hash mismatch (modified)"
        if r.get("seq") != seq + 1:
            return False, f"record {i}: sequence gap/duplicate/reorder (got {r.get('seq')}, want {seq + 1})"
        if r.get("prev") != prev:
            return False, f"record {i}: chain break (fork/deletion)"
        prev, seq = r["hash"], r["seq"]
    if expected_count is not None and seq != expected_count:
        return False, f"truncated: {seq} records, expected {expected_count}"
    if expected_head is not None and prev != expected_head:
        return False, "head mismatch (truncation or fork)"
    return True, "ok"
