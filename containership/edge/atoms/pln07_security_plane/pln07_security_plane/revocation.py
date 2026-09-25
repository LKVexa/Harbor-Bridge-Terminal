"""Durable revocation registry and propagation (MC-06, MC-10, MC-14, MC-29, MC-30).

* Append-only JSON-lines log, each record hash-chained to its predecessor and
  fsync'd before the call returns (crash consistency).  On open the log is
  replayed; a torn final line is truncated, any other corruption fails closed.
* Records are keyed by the **full SHA-256 fingerprint** (MC-14); the legacy
  16-hex id is carried alongside for 4.x verifiers.
* Writers hold a fencing ``epoch``.  A controller presenting an epoch lower
  than the highest one recorded is refused (stale-controller / split-brain
  protection) and duplicate revocations are idempotent.
* Sites acknowledge sequence numbers; ``horizon_breached`` reports sites that
  have not acknowledged a revocation within its horizon so they can be
  quarantined (MC-06).
* Tombstones are retained until ``not_after + retention`` then compacted.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .grants import Grant, SecurityPlaneError

GENESIS = "0" * 64


class RevocationError(SecurityPlaneError):
    code = "revocation.error"


class StaleEpoch(RevocationError):
    code = "revocation.stale_epoch"


class LogCorrupt(RevocationError):
    code = "revocation.corrupt"


def _canon(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


@dataclass
class RevocationRegistry:
    path: Path | None = None  # None -> in-memory (tests)
    retention: int = 86400
    _records: list[dict] = field(default_factory=list, init=False)
    _by_fp: dict[str, dict] = field(default_factory=dict, init=False)
    _by_legacy: dict[str, dict] = field(default_factory=dict, init=False)
    _acks: dict[str, int] = field(default_factory=dict, init=False)
    _epoch: int = field(default=0, init=False)
    _head: str = field(default=GENESIS, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.path is not None:
            self.path = Path(self.path)
            self._replay()

    # -- persistence -----------------------------------------------------------
    def _replay(self) -> None:
        if not self.path.exists():
            return
        raw = self.path.read_bytes()
        lines = raw.split(b"\n")
        good_len = 0
        for i, line in enumerate(lines):
            if not line:
                good_len += 1 if i < len(lines) - 1 else 0
                continue
            last = i == len(lines) - 1  # no trailing newline => torn write
            try:
                rec = json.loads(line)
                self._apply(rec, verify=True)
            except (ValueError, KeyError, LogCorrupt):
                if last:
                    break  # torn tail from a crash: drop it
                raise LogCorrupt("revocation log corrupt", details={"line": i + 1})
            good_len += len(line) + 1
        if good_len < len(raw):
            with open(self.path, "r+b") as fh:
                fh.truncate(good_len)
                fh.flush()
                os.fsync(fh.fileno())

    def _append(self, rec: dict) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "ab") as fh:
            fh.write(_canon(rec).encode() + b"\n")
            fh.flush()
            os.fsync(fh.fileno())

    def _apply(self, rec: dict, *, verify: bool) -> None:
        if verify:
            body = {k: v for k, v in rec.items() if k != "hash"}
            if rec["prev"] != self._head or hashlib.sha256(_canon(body).encode()).hexdigest() != rec["hash"]:
                raise LogCorrupt("hash chain broken", details={"seq": rec.get("seq")})
        self._records.append(rec)
        self._head = rec["hash"]
        self._epoch = max(self._epoch, rec["epoch"])
        if rec["op"] == "revoke":
            self._by_fp[rec["fingerprint"]] = rec
            self._by_legacy[rec["grant_id"]] = rec
        elif rec["op"] == "ack":
            self._acks[rec["site"]] = max(self._acks.get(rec["site"], 0), rec["upto"])
        elif rec["op"] == "compact":
            for fp in rec["removed"]:
                old = self._by_fp.pop(fp, None)
                if old:
                    self._by_legacy.pop(old["grant_id"], None)

    def _commit(self, body: dict) -> dict:
        body = {**body, "seq": len(self._records) + 1, "prev": self._head}
        rec = {**body, "hash": hashlib.sha256(_canon(body).encode()).hexdigest()}
        self._append(rec)  # durable first, then visible
        self._apply(rec, verify=False)
        return rec

    # -- API -------------------------------------------------------------------
    def revoke(self, grant: Grant, *, effective_at: int, horizon: int, epoch: int,
               reason: str = "", actor: str = "unknown") -> dict:
        if horizon < 0 or effective_at < 0:
            raise RevocationError("effective_at and horizon must be non-negative")
        with self._lock:
            if epoch < self._epoch:
                raise StaleEpoch("controller epoch is stale", details={"epoch": epoch, "current": self._epoch})
            existing = self._by_fp.get(grant.fingerprint)
            if existing is not None:
                return existing  # idempotent
            return self._commit({
                "op": "revoke", "type": "PK_REVOCATION/2", "fingerprint": grant.fingerprint,
                "grant_id": grant.id, "tenant": grant.tenant, "effective_at": effective_at,
                "horizon": horizon, "not_after": grant.not_after, "reason": reason[:1024],
                "actor": actor, "epoch": epoch,
            })

    def acknowledge(self, site: str, upto: int, *, epoch: int) -> None:
        with self._lock:
            if epoch < self._epoch:
                raise StaleEpoch("controller epoch is stale")
            self._commit({"op": "ack", "site": site, "upto": int(upto), "epoch": epoch})

    def is_revoked(self, grant: Grant) -> bool:
        with self._lock:
            return grant.fingerprint in self._by_fp or grant.id in self._by_legacy

    def pending_for(self, site: str) -> list[dict]:
        with self._lock:
            upto = self._acks.get(site, 0)
            return [r for r in self._records if r["op"] == "revoke" and r["seq"] > upto]

    def horizon_breached(self, sites: list[str], now: int) -> list[str]:
        with self._lock:
            return sorted({s for s in sites for r in self.pending_for(s)
                           if now > r["effective_at"] + r["horizon"]})

    def compact(self, now: int, *, epoch: int) -> int:
        with self._lock:
            removed = [fp for fp, r in self._by_fp.items() if now > r["not_after"] + self.retention]
            if removed:
                self._commit({"op": "compact", "removed": sorted(removed), "epoch": epoch})
            return len(removed)

    def export_legacy_ids(self) -> set[str]:
        with self._lock:
            return set(self._by_legacy)

    def verify_chain(self) -> bool:
        head = GENESIS
        for rec in self._records:
            body = {k: v for k, v in rec.items() if k != "hash"}
            if rec["prev"] != head or hashlib.sha256(_canon(body).encode()).hexdigest() != rec["hash"]:
                return False
            head = rec["hash"]
        return True

    @property
    def epoch(self) -> int:
        return self._epoch

    @property
    def head(self) -> str:
        return self._head

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"records": len(self._records), "revoked": len(self._by_fp),
                    "epoch": self._epoch, "head": self._head, "sites": dict(self._acks)}
