"""Component 29 - durable lease store (single-node, file-backed).

Record schema ``PK_DYN_LEASE/1`` (``LeaseRecord``):
  key (str, 1..128 chars [A-Za-z0-9._:/-]), holder (str, non-empty),
  epoch (int >= 1, fencing token), version (int >= 1, CAS version),
  expires (finite float, store clock), data (JSON object).

Semantics:
* ``cas(key, expected_version, ...)`` succeeds only when the stored version
  equals ``expected_version`` (0 = key must be absent); success bumps version
  by exactly 1.  Mismatch -> ``INV08.LEASE.CONFLICT`` (RETRYABLE: re-read).
* Fencing epochs come from a store-wide counter that never decreases, persisted
  with the records; every change of lease holder (or re-acquire after expiry)
  issues a strictly larger epoch.  ``check_fence`` rejects stale epochs with
  ``INV08.FENCE.STALE``.
* Every mutation is persisted before it returns: write temp file, fsync,
  ``os.replace`` then fsync the directory.  File carries a sha256 digest;
  mismatch on load -> ``INV08.STORE.CORRUPT`` (never silently reset).
* ``gc`` deletes leases expired longer than ``grace`` and reports orphans
  (holder not in the live set) without deleting unexpired ones.

Replication / consensus: NOT implemented (BLOCKED on a replicated consensus
store - etcd/Raft cluster - which is not available here).  This store is
linearizable only because it is a single process on a single node.
"""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .core import Inv08Error, Outcome, digest

SCHEMA = "PK_DYN_LEASE/1"
STORE_SCHEMA = "PK_DYN_LEASESTORE/1"
_KEY_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")

REPLICATION_MODEL = {
    "implemented": "single-node, fsync + atomic rename, linearizable within one process",
    "required_for_production": "replicated consensus store (e.g. Raft quorum) with linearizable CAS",
    "state": "BLOCKED",
    "blocker": "no replicated consensus cluster available to integrate or qualify against",
}


def _err(name: str, msg: str, outcome: Outcome, **details) -> Inv08Error:
    return Inv08Error(f"INV08.{name}", msg, outcome=outcome, details=details,
                      remediation={"LEASE.CONFLICT": "re-read and retry the CAS",
                                   "FENCE.STALE": "writer lost leadership/lease; stop writing",
                                   "STORE.UNAVAILABLE": "wait for store; retries are automatic",
                                   "STORE.CORRUPT": "run disaster bootstrap; file quarantined"}.get(name, ""))


@dataclass(frozen=True)
class LeaseRecord:
    key: str
    holder: str
    epoch: int
    version: int
    expires: float
    data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_record(asdict(self))


def validate_record(r: dict) -> None:
    if set(r) != {"key", "holder", "epoch", "version", "expires", "data"}:
        raise ValueError(f"lease record fields mismatch: {sorted(r)}")
    if not isinstance(r["key"], str) or not _KEY_RE.match(r["key"]):
        raise ValueError(f"bad lease key {r['key']!r}")
    if not isinstance(r["holder"], str) or not r["holder"]:
        raise ValueError("holder must be a non-empty string")
    for k in ("epoch", "version"):
        if isinstance(r[k], bool) or not isinstance(r[k], int) or r[k] < 1:
            raise ValueError(f"{k} must be int >= 1")
    if isinstance(r["expires"], bool) or not isinstance(r["expires"], (int, float)) \
            or not math.isfinite(r["expires"]):
        raise ValueError("expires must be finite")
    if not isinstance(r["data"], dict):
        raise ValueError("data must be an object")


def _atomic_write(path: Path, payload: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        dfd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


class LeaseStore:
    def __init__(self, path: str | os.PathLike, *, create: bool = True) -> None:
        self.path = Path(path)
        self.available = True          # fault-injection hook (component 46)
        self.write_count = 0
        self.last_write_ts: float | None = None
        self._records: dict[str, dict] = {}
        self._fence = 0
        if self.path.exists():
            self._load()
        elif create:
            self._persist(None)
        else:
            raise _err("STORE.MISSING", f"lease store {self.path} missing", Outcome.OPERATOR_REQUIRED)

    # -------------------------------------------------------------- durability
    def _load(self) -> None:
        try:
            doc = json.loads(self.path.read_bytes())
            body = doc["body"]
            if doc.get("digest") != digest(body) or body.get("schema") != STORE_SCHEMA:
                raise ValueError("digest/schema mismatch")
            for rec in body["records"].values():
                validate_record(rec)
            fence = body["fence"]
            if any(r["epoch"] > fence for r in body["records"].values()):
                raise ValueError("record epoch exceeds fence counter")
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise _err("STORE.CORRUPT", f"lease store unreadable: {exc}", Outcome.OPERATOR_REQUIRED,
                       path=str(self.path)) from None
        self._records, self._fence = body["records"], fence

    def _persist(self, ts: float | None) -> None:
        body = {"schema": STORE_SCHEMA, "fence": self._fence, "records": self._records}
        _atomic_write(self.path, json.dumps({"body": body, "digest": digest(body)},
                                            sort_keys=True).encode())
        self.write_count += 1
        if ts is not None:
            self.last_write_ts = ts

    def _check(self) -> None:
        if not self.available:
            raise _err("STORE.UNAVAILABLE", "lease store unavailable", Outcome.RETRYABLE_FAILURE)

    def ping(self) -> bool:
        self._check()
        return True

    # -------------------------------------------------------------- reads
    def get(self, key: str) -> LeaseRecord | None:
        self._check()
        r = self._records.get(key)
        return LeaseRecord(**r) if r else None

    def keys(self) -> list[str]:
        self._check()
        return sorted(self._records)

    @property
    def fence_counter(self) -> int:
        return self._fence

    # -------------------------------------------------------------- writes
    def cas(self, key: str, expected_version: int, *, holder: str, epoch: int, expires: float,
            data: dict | None = None, ts: float | None = None) -> LeaseRecord:
        self._check()
        cur = self._records.get(key)
        have = cur["version"] if cur else 0
        if have != expected_version:
            raise _err("LEASE.CONFLICT", f"version mismatch on {key}: have {have}, "
                       f"expected {expected_version}", Outcome.RETRYABLE_FAILURE,
                       key=key, have=have, expected=expected_version)
        if epoch > self._fence:
            raise ValueError("epoch must be issued by the store (issue_epoch)")
        rec = LeaseRecord(key, holder, epoch, have + 1, float(expires), dict(data or {}))
        old = self._records.get(key)
        self._records[key] = asdict(rec)
        try:
            self._persist(ts)
        except OSError:
            if old is None:
                self._records.pop(key, None)
            else:
                self._records[key] = old
            raise
        return rec

    def issue_epoch(self) -> int:
        self._check()
        self._fence += 1
        self._persist(None)
        return self._fence

    def acquire(self, key: str, holder: str, *, now: float, ttl: float,
                data: dict | None = None) -> LeaseRecord | None:
        """Acquire or renew.  Returns None when held by someone else."""
        if ttl <= 0:
            raise ValueError("ttl must be > 0")
        cur = self.get(key)
        if cur and cur.expires > now and cur.holder != holder:
            return None
        if cur and cur.expires > now and cur.holder == holder:
            epoch = cur.epoch                       # renewal keeps the token
        else:
            epoch = self.issue_epoch()              # new tenure -> new token
        return self.cas(key, cur.version if cur else 0, holder=holder, epoch=epoch,
                        expires=now + ttl, data=data if data is not None else (cur.data if cur else {}),
                        ts=now)

    def release(self, key: str, holder: str, epoch: int, *, now: float) -> bool:
        cur = self.get(key)
        if not cur or cur.holder != holder or cur.epoch != epoch:
            return False
        self._check()
        del self._records[key]
        self._persist(now)
        return True

    def check_fence(self, key: str, epoch: int) -> None:
        cur = self.get(key)
        if cur is None or epoch != cur.epoch:
            raise _err("FENCE.STALE", f"stale fencing token {epoch} for {key} "
                       f"(current {cur.epoch if cur else None})", Outcome.TERMINAL_FAILURE,
                       key=key, presented=epoch, current=cur.epoch if cur else None)

    def gc(self, *, now: float, grace: float, live_holders: set[str] | None = None) -> dict:
        self._check()
        removed, orphans = [], []
        for key, r in sorted(self._records.items()):
            if r["expires"] + grace <= now:
                removed.append(key)
            elif live_holders is not None and r["holder"] not in live_holders:
                orphans.append(key)
        for key in removed:
            del self._records[key]
        if removed:
            self._persist(now)
        return {"removed": removed, "orphaned_unexpired": orphans}
