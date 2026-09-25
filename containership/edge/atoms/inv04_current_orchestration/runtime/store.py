"""Versioned object store, optimistic concurrency and informer cache.

Components covered in-process:

* 4  ResourceVersion / optimistic concurrency — ``VersionedStore.update`` is a
  compare-and-swap on ``resource_version``; stale writers get ``Conflict``.
* 6  Durable desired-state adapter — ``VersionedStore`` persists to a JSONL
  snapshot + append log when ``path`` is given, tracks ``generation`` and
  ``observed_generation``.
* 2  Informer/watch cache — ``Informer`` does list+watch with bookmarks, a
  bounded watch window that expires (``Gone``) and forces relist, tombstones
  for deletes missed during a gap, and a ``has_synced`` barrier.

The real Kubernetes API server remains the authority in production; this
store is the reference implementation of the same semantics and the backing
store for tests, simulation and parity runs.
"""
from __future__ import annotations

import builtins
import json
import os
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .errors import AlreadyExists, Conflict, Gone, NotFound, StaleCache


@dataclass(frozen=True)
class Record:
    kind: str
    key: str
    uid: str
    resource_version: int
    generation: int
    observed_generation: int
    spec: Any
    status: Any = None


@dataclass(frozen=True)
class Event:
    type: str  # ADDED | MODIFIED | DELETED | BOOKMARK
    kind: str
    key: str
    resource_version: int
    record: Record | None


class VersionedStore:
    """Thread-safe store with global monotonically increasing resourceVersion."""

    def __init__(self, *, window: int = 1000, path: str | None = None, fsync: bool = True):
        self._lock = threading.RLock()
        self._objects: dict[tuple[str, str], Record] = {}
        self._rv = 0
        self._uid_seq = 0
        self._events: deque[Event] = deque(maxlen=window)
        self._watchers: list[Callable[[Event], None]] = []
        self._path = path
        self._fsync = fsync
        if path and os.path.exists(path):
            self._load(path)

    # ------------------------------------------------------------ persistence
    def _load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    op = json.loads(line)
                except json.JSONDecodeError:
                    # A torn final line from a crash is discarded; anything earlier is corruption.
                    rest = fh.read().strip()
                    if rest:
                        raise
                    break
                key = (op["kind"], op["key"])
                self._rv = max(self._rv, op["rv"])
                self._uid_seq = max(self._uid_seq, int(op.get("uid_seq", 0)))
                if op["op"] == "delete":
                    self._objects.pop(key, None)
                else:
                    self._objects[key] = Record(op["kind"], op["key"], op["uid"], op["rv"], op["gen"],
                                                op["ogen"], op["spec"], op.get("status"))

    def _persist(self, op: str, rec: Record) -> None:
        if not self._path:
            return
        line = json.dumps({"op": op, "kind": rec.kind, "key": rec.key, "uid": rec.uid, "rv": rec.resource_version,
                           "gen": rec.generation, "ogen": rec.observed_generation, "spec": rec.spec,
                           "status": rec.status, "uid_seq": self._uid_seq}, sort_keys=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            if self._fsync:
                os.fsync(fh.fileno())

    # ------------------------------------------------------------------- CRUD
    @property
    def resource_version(self) -> int:
        with self._lock:
            return self._rv

    def get(self, kind: str, key: str) -> Record:
        with self._lock:
            try:
                return self._objects[(kind, key)]
            except KeyError:
                raise NotFound(f"{kind} {key} not found", details={"kind": kind, "key": key}) from None

    def list(self, kind: str) -> "tuple[builtins.list[Record], int]":
        with self._lock:
            items = sorted((r for (k, _), r in self._objects.items() if k == kind), key=lambda r: r.key)
            return items, self._rv

    def create(self, kind: str, key: str, spec: Any, *, uid: str | None = None) -> Record:
        with self._lock:
            if (kind, key) in self._objects:
                raise AlreadyExists(f"{kind} {key} exists", details={"kind": kind, "key": key})
            self._rv += 1
            self._uid_seq += 1
            rec = Record(kind, key, uid or f"{kind.lower()}-{self._uid_seq}", self._rv, 1, 0, _clone(spec))
            self._objects[(kind, key)] = rec
            self._persist("put", rec)
            self._emit(Event("ADDED", kind, key, self._rv, rec))
            return rec

    def update(self, kind: str, key: str, spec: Any, *, expected_rv: int, uid: str | None = None) -> Record:
        """Compare-and-swap spec update; bumps generation when spec changes."""
        with self._lock:
            cur = self.get(kind, key)
            if uid is not None and uid != cur.uid:
                raise Conflict(f"{kind} {key} uid changed ({cur.uid} != {uid}); object was recreated",
                               details={"kind": kind, "key": key})
            if cur.resource_version != expected_rv:
                raise Conflict(f"{kind} {key} resourceVersion {expected_rv} is stale (current {cur.resource_version})",
                               details={"kind": kind, "key": key, "current": cur.resource_version})
            self._rv += 1
            gen = cur.generation + (1 if spec != cur.spec else 0)
            rec = Record(kind, key, cur.uid, self._rv, gen, cur.observed_generation, _clone(spec), cur.status)
            self._objects[(kind, key)] = rec
            self._persist("put", rec)
            self._emit(Event("MODIFIED", kind, key, self._rv, rec))
            return rec

    def update_status(self, kind: str, key: str, status: Any, *, expected_rv: int, observed_generation: int) -> Record:
        with self._lock:
            cur = self.get(kind, key)
            if cur.resource_version != expected_rv:
                raise Conflict(f"{kind} {key} status write is stale", details={"kind": kind, "key": key})
            if observed_generation > cur.generation:
                raise StaleCache("observed_generation cannot exceed generation")
            self._rv += 1
            rec = Record(kind, key, cur.uid, self._rv, cur.generation, observed_generation, cur.spec, _clone(status))
            self._objects[(kind, key)] = rec
            self._persist("put", rec)
            self._emit(Event("MODIFIED", kind, key, self._rv, rec))
            return rec

    def delete(self, kind: str, key: str, *, expected_rv: int | None = None, uid: str | None = None) -> None:
        with self._lock:
            cur = self.get(kind, key)
            if uid is not None and cur.uid != uid:
                raise Conflict(f"{kind} {key} uid precondition failed", details={"kind": kind, "key": key})
            if expected_rv is not None and cur.resource_version != expected_rv:
                raise Conflict(f"{kind} {key} delete precondition stale", details={"kind": kind, "key": key})
            self._rv += 1
            del self._objects[(kind, key)]
            tomb = Record(kind, key, cur.uid, self._rv, cur.generation, cur.observed_generation, cur.spec, cur.status)
            self._persist("delete", tomb)
            self._emit(Event("DELETED", kind, key, self._rv, tomb))

    # ------------------------------------------------------------------ watch
    def _emit(self, ev: Event) -> None:
        self._events.append(ev)
        for w in list(self._watchers):
            w(ev)

    def events_since(self, rv: int, kind: str | None = None) -> "builtins.list[Event]":
        """Return events after ``rv``; raise ``Gone`` if the window no longer covers it."""
        with self._lock:
            if rv < self._rv and (not self._events or self._events[0].resource_version > rv + 1):
                raise Gone(f"resourceVersion {rv} is older than the watch window", details={"rv": rv})
            out = [e for e in self._events if e.resource_version > rv and (kind is None or e.kind == kind)]
            out.append(Event("BOOKMARK", kind or "*", "", self._rv, None))
            return out

    def subscribe(self, fn: Callable[[Event], None]) -> Callable[[], None]:
        with self._lock:
            self._watchers.append(fn)
        return lambda: self._watchers.remove(fn)


def _clone(v: Any) -> Any:
    return json.loads(json.dumps(v)) if v is not None else None


class Informer:
    """List/watch cache with relist-on-expiry, tombstones and a sync barrier.

    ``poll()`` drives one watch step (pull model keeps it deterministic and
    testable).  ``max_staleness_rv`` lets writers reject decisions made on a
    cache that has fallen too far behind (component 52).
    """

    def __init__(self, store: VersionedStore, kind: str, *, on_event: Callable[[str, Record], None] | None = None):
        self.store = store
        self.kind = kind
        self.cache: dict[str, Record] = {}
        self.last_rv = 0
        self.synced = False
        self.relists = 0
        self.tombstones: list[Record] = []
        self._on_event = on_event or (lambda t, r: None)

    def has_synced(self) -> bool:
        return self.synced

    def relist(self) -> None:
        items, rv = self.store.list(self.kind)
        fresh = {r.key: r for r in items}
        for key, old in self.cache.items():
            if key not in fresh:
                # deleted while we were not watching -> synthesize tombstone
                self.tombstones.append(old)
                self._on_event("DELETED", old)
        for key, rec in fresh.items():
            prev = self.cache.get(key)
            if prev is None or prev.resource_version != rec.resource_version:
                self._on_event("ADDED" if prev is None else "MODIFIED", rec)
        self.cache = fresh
        self.last_rv = rv
        self.synced = True
        self.relists += 1

    def poll(self) -> int:
        """Apply pending watch events; relist on ``Gone``. Returns events applied."""
        if not self.synced:
            self.relist()
            return len(self.cache)
        try:
            events = self.store.events_since(self.last_rv, self.kind)
        except Gone:
            self.relist()
            return len(self.cache)
        n = 0
        for ev in events:
            if ev.type == "BOOKMARK":
                self.last_rv = max(self.last_rv, ev.resource_version)
                continue
            if ev.resource_version <= self.last_rv:
                continue  # duplicate / reordered delivery is ignored
            if ev.type == "DELETED":
                self.cache.pop(ev.key, None)
            else:
                self.cache[ev.key] = ev.record  # type: ignore[assignment]
            self.last_rv = ev.resource_version
            self._on_event(ev.type, ev.record)  # type: ignore[arg-type]
            n += 1
        return n

    def require_fresh(self, max_lag: int) -> None:
        lag = self.store.resource_version - self.last_rv
        if not self.synced or lag > max_lag:
            raise StaleCache(f"{self.kind} informer lag {lag} exceeds {max_lag}", details={"lag": lag})

    def items(self) -> Iterable[Record]:
        return [self.cache[k] for k in sorted(self.cache)]
