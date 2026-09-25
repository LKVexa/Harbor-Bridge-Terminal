"""GAP-05 replication/consistency integration contract (MC-041) and site
fencing used by disaster recovery (MC-040-03).

Model: one *authoritative* site per namespace set holds write authority at a
monotonically increasing **site epoch**.  Followers apply the authoritative
event stream in order.  Failover promotes a follower with ``epoch + 1``; the
old primary, when it reconnects, sees a higher epoch and demotes itself, and
any replicated batch or write carrying a stale epoch is refused with
``CSTATE_FENCED`` (MC-041-04).  Conflict ownership (MC-041-05): there are no
multi-writer conflicts by construction; divergence (a follower holding a
revision the new primary does not) is *detected* by comparing
``(revision, event digest)`` and resolved by relisting from the primary
snapshot -- never merged.

Wire handshake ``cstate.repl/1.0`` (MC-041-01)::

    {"schema":"cstate.repl_hello/1.0","site":"site-b","epoch":3,"last_applied":1200,
     "digest":"<sha256 of events up to last_applied or ''>"}
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any

from .errors import CompactedError, Fenced, IncompatibleVersion, InvalidArgument
from .store import ControlStore, Event

REPL_SCHEMA = "cstate.repl_batch/1.0"


def events_digest(prev: str, events: list[dict[str, Any]]) -> str:
    h = hashlib.sha256(prev.encode())
    for e in events:
        h.update(json.dumps(e, sort_keys=True).encode())
    return h.hexdigest()


class ReplicationSource:
    """Serves ordered batches from the authoritative store."""

    def __init__(self, store: ControlStore, site: str, epoch: int) -> None:
        self.store, self.site, self.epoch = store, site, epoch

    def hello(self, msg: dict[str, Any]) -> dict[str, Any]:
        if not str(msg.get("schema", "")).startswith("cstate.repl_hello/1."):
            raise IncompatibleVersion("replication protocol major mismatch", supported=["cstate.repl_hello/1.0"])
        if int(msg.get("epoch", 0)) > self.epoch:
            raise Fenced("peer holds a newer epoch; this site must demote", reason="stale_primary")
        return {"schema": "cstate.repl_hello/1.0", "site": self.site, "epoch": self.epoch,
                "revision": self.store.revision, "compact_revision": self.store.compact_revision}

    def batch(self, from_rev: int, max_events: int = 1000) -> dict[str, Any]:
        allev = self.store.events_since(from_rev)  # raises Compacted -> follower must resync
        evs = []
        for e in allev:  # never split a revision across batches
            if len(evs) >= max_events and e.revision != evs[-1].revision:
                break
            evs.append(e)
        return {"schema": REPL_SCHEMA, "site": self.site, "epoch": self.epoch, "from": from_rev,
                "events": [e.to_dict() for e in evs], "head": self.store.revision}

    def snapshot(self) -> dict[str, Any]:
        return {"schema": "cstate.repl_snapshot/1.0", "epoch": self.epoch, "state": self.store.export_state()}


@dataclass
class ReplicaStatus:
    site: str
    epoch: int
    applied: int
    head: int
    digest: str

    @property
    def lag(self) -> int:
        return max(0, self.head - self.applied)


class ReplicaApplier:
    """Applies batches to a follower store with epoch fencing and ordering checks."""

    def __init__(self, store: ControlStore, site: str, *, max_safe_lag: int = 100, durable: Any = None) -> None:
        self.store, self.site, self.max_safe_lag, self.durable = store, site, max_safe_lag, durable
        self.epoch = 0
        self.head = store.revision
        self.digest = ""
        self._lock = threading.Lock()

    def apply(self, batch: dict[str, Any]) -> int:
        if batch.get("schema") != REPL_SCHEMA:
            raise IncompatibleVersion("unsupported replication batch schema", supported=[REPL_SCHEMA])
        with self._lock:
            ep = int(batch["epoch"])
            if ep < self.epoch:
                raise Fenced("batch from stale epoch refused", reason="stale_epoch")
            self.epoch = ep
            evs = batch["events"]
            groups: dict[int, list[dict[str, Any]]] = {}
            for e in evs:
                groups.setdefault(e["revision"], []).append(e)
            n = 0
            for rev in sorted(groups):
                if rev <= self.store.revision:
                    continue  # duplicate delivery: idempotent
                if rev != self.store.revision + 1:
                    raise InvalidArgument(f"replication gap: have {self.store.revision}, got {rev}; resync",
                                          field="events", resume_revision=self.store.revision + 1)
                self.store._commit({"t": "txn", "v": 1, "rev": rev, "events": groups[rev]})
                self.digest = events_digest(self.digest, groups[rev])
                n += len(groups[rev])
            self.head = max(self.head, int(batch.get("head", self.store.revision)))
            return n

    def resync(self, snap: dict[str, Any]) -> None:
        with self._lock:
            if int(snap["epoch"]) < self.epoch:
                raise Fenced("snapshot from stale epoch refused", reason="stale_epoch")
            self.store.load_state(snap["state"])
            self.epoch = int(snap["epoch"])
            self.digest = ""
            if self.durable is not None:  # a resync replaces state wholesale: persist it as a new snapshot
                self.durable.checkpoint()

    def status(self) -> ReplicaStatus:
        return ReplicaStatus(self.site, self.epoch, self.store.revision, self.head, self.digest)

    def safe_to_read(self) -> bool:
        """Bounded-staleness read boundary (MC-041-03)."""
        return self.status().lag <= self.max_safe_lag


def sync_once(src: ReplicationSource, dst: ReplicaApplier, max_events: int = 1000) -> int:
    """Pull one batch; on compaction, fall back to full snapshot resync (MC-041-06)."""
    try:
        return dst.apply(src.batch(dst.store.revision + 1, max_events))
    except CompactedError:
        dst.resync(src.snapshot())
        return -1
