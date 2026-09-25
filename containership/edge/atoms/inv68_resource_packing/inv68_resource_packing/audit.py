"""Tamper-evident security audit ledger (INV-68 MC-15; C049, C090).

Adapted from the owner's INV-44 v4.3.0 ``audit_log.py`` (hash chain + optional
HMAC + external head anchor). Additions (carried from INV-64 4.3.0):

* event schema ``PK_PACK_AUDIT/1`` with ``event_id``, ``operation``,
  ``resource``, ``reason``, ``correlation_id`` and the active
  ``versions`` (release / policy / trust / config) on every record;
* bounded buffering when the sink is unwritable: records are held in order
  (at most ``buffer_limit``); beyond that events are *counted* as dropped and
  an ``audit.loss`` record carrying the count is chained in on recovery, so
  loss is visible in the ledger itself, never silent;
* ``fail_closed=True`` appends raise instead of buffering — used for
  activation/rollback/policy changes, which must not proceed unaudited;
* :meth:`seal` writes an HMAC-authenticated checkpoint (seq, head hash) to a
  separate anchor file; ``verify(anchor=...)`` detects tail truncation and a
  rewritten history that no longer reaches the sealed head;
* ``python -m inv68_resource_packing.audit verify LEDGER [--anchor A --key-env VAR]``
  prints a machine-readable verdict.

Details are passed through :func:`redaction.redact` before hashing, so the
chain never commits to secret bytes; JSON encoding neutralises log injection.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path

from .redaction import redact

AUDIT_SCHEMA = "PK_PACK_AUDIT/1"
GENESIS = "0" * 64


class AuditChainBroken(Exception):
    def __init__(self, message: str, **info):
        self.info = info
        super().__init__(f"{message} {info}" if info else message)


class AuditUnavailable(Exception):
    pass


def _canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class AuditLog:
    def __init__(self, path: str | os.PathLike, *, mac_key: bytes | None = None, clock=time.time,
                 buffer_limit: int = 1_000, metrics=None, versions: dict | None = None,
                 opener=None):
        self.path = Path(path)
        self._mac_key = mac_key
        self._clock = clock
        self._lock = threading.Lock()
        self._buffer: deque[dict] = deque()
        self._buffer_limit = buffer_limit
        self._metrics = metrics
        self.versions = dict(versions or {})
        self.dropped = 0
        self._unreported_drops = 0
        self._open = opener or (lambda p: p.open("a", encoding="utf-8"))
        self._seq, self._prev = self._scan_tail()

    # ---------------------------------------------------------------- reading
    def _records(self):
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AuditChainBroken("unparseable audit record", line=lineno) from exc

    def _scan_tail(self) -> tuple[int, str]:
        seq, prev = 0, GENESIS
        for rec in self._records() or ():
            seq, prev = rec["seq"], rec["hash"]
        return seq, prev

    def records(self, *, tenant: str | None = None) -> list[dict]:
        return [r for r in (self._records() or ()) if tenant is None or r.get("tenant") == tenant]

    # ---------------------------------------------------------------- writing
    def _chain(self, body: dict) -> dict:
        rec = dict(body, seq=self._seq + 1, prev=self._prev)
        if self._mac_key is not None:
            rec["mac"] = hmac.new(self._mac_key, _canon(rec), hashlib.sha256).hexdigest()
        rec["hash"] = hashlib.sha256(_canon(rec)).hexdigest()
        self._seq, self._prev = rec["seq"], rec["hash"]
        return rec

    def _flush(self) -> None:
        if not self._buffer:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._open(self.path) as fh:
            while self._buffer:
                fh.write(json.dumps(self._buffer[0], sort_keys=True) + "\n")
                self._buffer.popleft()
            fh.flush()
            os.fsync(fh.fileno())

    def append(self, operation: str, *, actor: str, tenant: str | None = None, outcome: str,
               resource: str | None = None, reason: str | None = None, correlation_id: str | None = None,
               fail_closed: bool = False, **detail) -> dict | None:
        with self._lock:
            if self._buffer:  # sink may have recovered: drain the backlog first, in order
                try:
                    self._flush()
                except OSError:
                    pass
            if self._unreported_drops and len(self._buffer) < self._buffer_limit:
                self._buffer.append(self._chain(self._body("audit.loss", "inv68", None, "recorded", None,
                                                           "sink outage", None,
                                                           {"dropped": self._unreported_drops})))
                self._unreported_drops = 0
            if len(self._buffer) >= self._buffer_limit:
                if fail_closed:
                    raise AuditUnavailable("audit sink unavailable and buffer full")
                self.dropped += 1
                self._unreported_drops += 1
                if self._metrics:
                    self._metrics.inc("inv68_audit_dropped_total")
                return None
            rec = self._chain(self._body(operation, actor, tenant, outcome, resource, reason,
                                         correlation_id, detail))
            self._buffer.append(rec)
            try:
                self._flush()
            except OSError:
                if fail_closed:
                    # un-chain: the record never left memory, so roll the head back
                    self._buffer.pop()
                    self._seq, self._prev = rec["seq"] - 1, rec["prev"]
                    raise AuditUnavailable("audit sink unavailable")
            if self._metrics:
                self._metrics.set("inv68_audit_buffered", len(self._buffer))
            return rec

    def _body(self, operation, actor, tenant, outcome, resource, reason, correlation_id, detail) -> dict:
        return {
            "schema": AUDIT_SCHEMA,
            "event_id": str(uuid.uuid4()),
            "ts": round(float(self._clock()), 6),
            "operation": str(operation)[:64],
            "actor": str(actor)[:256],
            "tenant": tenant,
            "resource": resource,
            "outcome": str(outcome)[:32],
            "reason": reason,
            "correlation_id": correlation_id,
            "versions": dict(self.versions),
            "detail": redact(detail),
        }

    def head(self) -> tuple[int, str]:
        with self._lock:
            return self._seq, self._prev

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    # ---------------------------------------------------------------- sealing
    def seal(self, anchor_path: str | os.PathLike, *, key: bytes) -> dict:
        with self._lock:
            self._flush()
            cp = {"schema": "PK_PACK_AUDIT_ANCHOR/1", "seq": self._seq, "hash": self._prev,
                  "ts": round(float(self._clock()), 6)}
        cp["mac"] = hmac.new(key, _canon(cp), hashlib.sha256).hexdigest()
        p = Path(anchor_path)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(cp, sort_keys=True), encoding="utf-8")
        os.replace(tmp, p)
        return cp

    # ------------------------------------------------------------- verifying
    def verify(self, *, expected_head: tuple[int, str] | None = None,
               anchor_path: str | os.PathLike | None = None, anchor_key: bytes | None = None) -> int:
        """Return the record count, or raise :class:`AuditChainBroken`."""
        anchor = None
        if anchor_path is not None:
            cp = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
            mac = cp.pop("mac", "")
            if anchor_key is None or not hmac.compare_digest(
                    mac, hmac.new(anchor_key, _canon(cp), hashlib.sha256).hexdigest()):
                raise AuditChainBroken("anchor MAC invalid")
            anchor = (cp["seq"], cp["hash"])
        prev, seq = GENESIS, 0
        seen_ids = set()
        anchor_ok = anchor is None
        for rec in self._records() or ():
            claimed = rec.get("hash")
            body = {k: v for k, v in rec.items() if k != "hash"}
            if rec.get("seq") != seq + 1:
                raise AuditChainBroken("sequence gap, duplicate or reorder", at=seq + 1)
            if rec.get("prev") != prev:
                raise AuditChainBroken("prev-hash mismatch", at=rec.get("seq"))
            if hashlib.sha256(_canon(body)).hexdigest() != claimed:
                raise AuditChainBroken("record hash mismatch", at=rec.get("seq"))
            if rec.get("event_id") in seen_ids:
                raise AuditChainBroken("duplicate event id", at=rec.get("seq"))
            seen_ids.add(rec.get("event_id"))
            if self._mac_key is not None:
                mac = body.pop("mac", None)
                want = hmac.new(self._mac_key, _canon(body), hashlib.sha256).hexdigest()
                if mac is None or not hmac.compare_digest(mac, want):
                    raise AuditChainBroken("record MAC mismatch", at=rec.get("seq"))
            prev, seq = claimed, rec["seq"]
            if anchor is not None and (seq, prev) == tuple(anchor):
                anchor_ok = True
        if not anchor_ok:
            raise AuditChainBroken("sealed checkpoint not found in chain (truncation or rewrite)", want=anchor[0])
        if expected_head is not None and (seq, prev) != tuple(expected_head):
            raise AuditChainBroken("chain head does not match external anchor (truncation?)",
                                   have=seq, want=expected_head[0])
        return seq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv68-audit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("ledger")
    v.add_argument("--anchor")
    v.add_argument("--key-env", help="environment variable holding the hex anchor/MAC key")
    a = ap.parse_args(argv)
    key = bytes.fromhex(os.environ[a.key_env]) if a.key_env and a.key_env in os.environ else None
    log = AuditLog(a.ledger, mac_key=key)
    try:
        n = log.verify(anchor_path=a.anchor, anchor_key=key)
        out = {"schema": "PK_PACK_AUDIT_VERIFY/1", "ledger": a.ledger, "result": "PASS", "records": n,
               "head": list(log.head())}
        code = 0
    except (AuditChainBroken, OSError, ValueError, KeyError) as exc:
        out = {"schema": "PK_PACK_AUDIT_VERIFY/1", "ledger": a.ledger, "result": "FAIL", "error": str(exc)}
        code = 2
    print(json.dumps(out, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
