"""Watch sessions: ordered delivery, progress notifications, resume, bounded
buffering and slow-consumer control (MC-014, MC-015, MC-017).

Guarantees (normative):

* **Ordering** -- within one watch, events are delivered in strictly increasing
  ``(revision, index)`` order; a transaction's events are delivered together in
  one frame (MC-014-02).
* **No silent gaps** -- a watch is created atomically with its catch-up read
  under the store lock.  A start revision at or below the compaction point is
  refused with ``CSTATE_COMPACTED`` (MC-017-03).  If the per-watch queue
  overflows, the watch is *cancelled* with ``CSTATE_SLOW_CONSUMER`` and a
  ``resume_revision`` -- events are never dropped from a live watch
  (MC-015-03).
* **Progress** -- ``progress`` frames carry the store revision and never
  fabricate state changes; clients use them for liveness and as a safe resume
  point (MC-014-03, MC-015-06).
* **Resume** -- the resume token is the next revision to request:
  ``last_delivered_revision + 1`` or ``progress_revision + 1`` (MC-015-01).
* **Drain** -- :meth:`WatchHub.drain` sends every watch a terminal
  ``CSTATE_DRAINING`` frame within a bounded grace period (MC-031-02).
"""
from __future__ import annotations

import itertools
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import CompactedError, Draining, LimitExceeded, QuotaExceeded, SlowConsumer, StateError
from .limits import validate_revision
from .store import ControlStore, Event


@dataclass
class Frame:
    type: str                       # events | progress | canceled
    revision: int
    events: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None
    watch_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type, "watch_id": self.watch_id, "revision": self.revision}
        if self.events:
            d["events"] = self.events
        if self.error:
            d["error"] = self.error
        return d


class Watcher:
    """One watch.  Two delivery modes, switched atomically under the store lock:

    * **live** -- commits are pushed into a bounded queue by the store listener;
    * **catch-up** -- the watcher pulls pages straight from retained history.

    A new watch starts in catch-up mode from its start revision.  When the live
    queue would overflow, the watcher falls back to catch-up instead of dropping
    events (lossless backpressure through shared history, MC-015-03).  It is
    cancelled only if (a) compaction overtakes its position (``CSTATE_COMPACTED``,
    client relists) or (b) it lags the head by more than ``max_lag`` revisions
    (``CSTATE_SLOW_CONSUMER``) so a dead consumer cannot pin compaction forever.
    """

    def __init__(self, hub: "WatchHub", wid: int, prefix: str, owner: str, max_queue: int,
                 kinds: frozenset[str] | None, with_prev: bool,
                 transform: Callable[[dict[str, Any]], dict[str, Any] | None] | None,
                 start_revision: int, max_lag: int) -> None:
        self.hub, self.id, self.prefix, self.owner = hub, wid, prefix, owner
        self.max_queue = max_queue
        self.kinds = kinds
        self.with_prev = with_prev
        self.transform = transform
        self.start_revision = start_revision
        self.max_lag = max_lag
        self._q: deque[Frame] = deque()
        self._queued_events = 0
        self._cv = threading.Condition()
        self.closed = False
        self.catchup_next = start_revision   # >0 => catch-up mode, next revision to read
        self.last_revision = 0
        self.delivered = 0
        self.fallbacks = 0

    def _select(self, evs: list[Event]) -> list[dict[str, Any]]:
        sel = []
        for e in evs:
            if not e.key.startswith(self.prefix) or (self.kinds and e.kind not in self.kinds):
                continue
            d = e.to_dict()
            if not self.with_prev:
                d.pop("prev_value", None)
            if self.transform:
                d = self.transform(d)
                if d is None:
                    continue
            sel.append(d)
        return sel

    # called under store lock ------------------------------------------------
    def _offer(self, evs: list[Event], rev: int) -> None:
        if self.closed or self.catchup_next:
            return
        sel = self._select(evs)
        if not sel:
            return
        with self._cv:
            if self._queued_events + len(sel) > self.max_queue:
                self.catchup_next = rev  # lossless fallback: re-read from history
                self.fallbacks += 1
                self.hub._count("slow_consumer_fallbacks")
                self._cv.notify_all()
                return
            self._q.append(Frame("events", rev, sel, watch_id=self.id))
            self._queued_events += len(sel)
            self._cv.notify_all()

    def _resume_point(self) -> int:
        if self.catchup_next:
            return self.catchup_next
        return self.last_revision + 1 if self.last_revision else self.start_revision

    def _cancel_locked(self, err: StateError) -> None:
        self._q.clear()
        self._queued_events = 0
        self._q.append(Frame("canceled", self.hub.store.revision, error=err.to_wire(), watch_id=self.id))
        self.closed = True
        self._cv.notify_all()
        self.hub._forget(self.id)

    def _fill_from_history(self) -> None:
        """Pull up to ``max_queue`` events of catch-up.  Lock order: store -> cv
        (the same order the commit listener uses), so no inversion."""
        store = self.hub.store
        with store.lock, self._cv:
            if not self.catchup_next or self.closed:
                return
            nxt = self.catchup_next
            if store.revision - nxt + 1 > self.max_lag:
                self.hub._count("slow_consumer_cancels")
                self._cancel_locked(SlowConsumer("watch lagged too far behind head; resume or relist",
                                                 resume_revision=nxt))
                return
            try:
                evs = store.events_since(nxt, self.prefix)
            except CompactedError as exc:
                self.hub._count("compacted_refusals")
                self._cancel_locked(CompactedError(str(exc), compact_revision=store.compact_revision,
                                                   resume_revision=nxt))
                return
            budget = self.max_queue - self._queued_events
            group: list[Event] = []
            last_rev = nxt - 1
            for e in evs:
                if group and group[-1].revision != e.revision:
                    if not self._push_group(group, budget):
                        self.catchup_next = group[0].revision
                        return
                    budget -= len(group)
                    last_rev = group[-1].revision
                    group = []
                group.append(e)
            if group:
                if not self._push_group(group, budget):
                    self.catchup_next = group[0].revision
                    return
            # fully caught up to the head while holding the store lock: go live
            self.catchup_next = 0
            self._cv.notify_all()

    def _push_group(self, group: list[Event], budget: int) -> bool:
        sel = self._select(group)
        if not sel:
            return True
        if len(sel) > budget and self._q:
            return False
        self._q.append(Frame("events", group[-1].revision, sel, watch_id=self.id))
        self._queued_events += len(sel)
        return True

    # consumer API -----------------------------------------------------------
    def poll(self, timeout: float = 1.0) -> Frame:
        """Return the next frame; a ``progress`` frame if nothing arrives in *timeout*."""
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            with self._cv:
                need_fill = not self._q and self.catchup_next and not self.closed
            if need_fill:
                self._fill_from_history()
            with self._cv:
                if self._q:
                    break
                if self.closed:
                    return Frame("canceled", self.hub.store.revision,
                                 error={"code": "CSTATE_CANCELLED", "category": "cancellation",
                                        "retryable": False, "message": "watch closed", "details": {}},
                                 watch_id=self.id)
                if self.catchup_next:
                    continue
                left = deadline - time.monotonic()
                if left > 0:
                    self._cv.wait(left)
                    continue
            # progress: read the head under the store lock so no commit is mid-offer
            with self.hub.store.lock, self._cv:
                if not self._q and not self.catchup_next and not self.closed:
                    return Frame("progress", self.hub.store.revision, watch_id=self.id)
        with self._cv:
            f = self._q.popleft()
            if f.type == "events":
                self._queued_events -= len(f.events)
                self.last_revision = f.revision
                self.delivered += len(f.events)
            if f.type == "canceled":
                self.closed = True
            return f

    @property
    def backlog(self) -> int:
        return self._queued_events

    @property
    def catching_up(self) -> bool:
        return bool(self.catchup_next)

    def cancel(self) -> None:
        self.hub.cancel(self.id)


class WatchHub:
    """Registry of live watches attached to one :class:`ControlStore`."""

    def __init__(self, store: ControlStore, *, max_queue: int | None = None, max_per_owner: int | None = None,
                 max_total: int | None = None, max_lag: int | None = None) -> None:
        self.store = store
        self.max_queue = max_queue or store.limits.max_watch_queue_events
        self.max_per_owner = max_per_owner or store.limits.max_watches_per_identity
        self.max_total = max_total or store.limits.max_watches_total
        self._watchers: dict[int, Watcher] = {}
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self.draining = False
        self.max_lag = max_lag or store.limits.max_history_events
        self.counters = {"watches_created": 0, "slow_consumer_cancels": 0, "slow_consumer_fallbacks": 0,
                         "compacted_refusals": 0, "drained": 0}
        store.add_listener(self._on_commit)

    def _count(self, name: str, n: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + n

    def _forget(self, wid: int) -> None:
        with self._lock:
            self._watchers.pop(wid, None)

    def _on_commit(self, evs: list[Event], rev: int) -> None:
        with self._lock:
            ws = list(self._watchers.values())
        for w in ws:
            w._offer(evs, rev)

    def create(self, *, prefix: str = "", start_revision: int = 0, owner: str = "",
               kinds: set[str] | None = None, with_prev: bool = False,
               transform: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None) -> Watcher:
        if self.draining:
            raise Draining("server is draining; reconnect to another member")
        with self.store.lock:  # atomic catch-up + registration: no race with commits
            with self._lock:
                if len(self._watchers) >= self.max_total:
                    raise LimitExceeded("global watch limit reached", limit="max_watches_total",
                                        limit_value=self.max_total)
                if owner and sum(1 for w in self._watchers.values() if w.owner == owner) >= self.max_per_owner:
                    raise QuotaExceeded("per-identity watch quota reached", limit="max_watches_per_identity",
                                        limit_value=self.max_per_owner, retry_after_s=1.0)
            if start_revision:
                # validates compaction/format now so the caller gets a synchronous error
                validate_revision(start_revision, "start_revision")
                if start_revision <= self.store.compact_revision:
                    self._count("compacted_refusals")
                    raise CompactedError(f"revision {start_revision} compacted; relist",
                                         compact_revision=self.store.compact_revision, revision=start_revision)
            start = start_revision or self.store.revision + 1
            w = Watcher(self, next(self._ids), prefix, owner, self.max_queue,
                        frozenset(kinds) if kinds else None, with_prev, transform, start, self.max_lag)
            if start > self.store.revision:
                w.catchup_next = 0  # nothing to catch up: live immediately
            with self._lock:
                self._watchers[w.id] = w
                self._count("watches_created")
            return w

    def cancel(self, wid: int) -> None:
        with self._lock:
            w = self._watchers.pop(wid, None)
        if w:
            with w._cv:
                w.closed = True
                w._cv.notify_all()

    def drain(self, grace_s: float = 5.0) -> int:
        """Stop admitting watches, send terminal DRAINING frames, wait <= grace."""
        self.draining = True
        with self._lock:
            ws = list(self._watchers.values())
        for w in ws:
            with w._cv:
                w._q.append(Frame("canceled", self.store.revision,
                                  error=Draining("server draining", resume_revision=w._resume_point()).to_wire(),
                                  watch_id=w.id))
                w._cv.notify_all()
        end = time.monotonic() + grace_s
        while time.monotonic() < end and any(w._q for w in ws):
            time.sleep(0.01)
        for w in ws:
            self.cancel(w.id)
        self._count("drained", len(ws))
        return len(ws)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            ws = list(self._watchers.values())
        return {"active": len(ws), "backlog_total": sum(w.backlog for w in ws),
                "max_backlog": max((w.backlog for w in ws), default=0), **self.counters}
