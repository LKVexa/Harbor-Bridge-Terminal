"""INV-15 v4.3.0 host-side waitable table (components 9-30, 39-54 runtime parts).

This is the *reference host*: a complete, thread-safe, stdlib-only model of the
production semantics. It is not the production host backend (component 19):
it uses a Python lock and Python containers, and it says so in every place a
checklist item asks for runtime-native primitives.

Linearization points (all under ``AsyncHost._lock``):
  allocation   = row stored into ``_slots[slot]``
  publication  = row.state leaves PENDING (payload and metadata are written to
                 the row before the state field changes, inside the same critical
                 section; readers only read under the lock -> happens-before via
                 the lock's acquire/release)
  wait/subscribe registration = waiter added to row.waiters, then state re-checked
                 in the same critical section (check-and-subscribe)
  take/cancel/invalidate/reclaim = row removed from ``_slots`` and slot
                 generation incremented
Callbacks (subscribers, on_ready hooks, payload release) always run after the
lock is released, so user code can never extend a critical section.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
import hashlib
import heapq
import hmac
import secrets
import sys
import threading
import time
from typing import Any, Callable, Iterable

from . import handles as H
from .errors import (AbiError, BudgetExhaustedError, CalleeTrapped, CallTimeout, CancelAck,
                     CancelReason, DeadlineExceeded, Disabled, Draining, DuplicatePublication,
                     ErrorCode, ForeignHandleError, HandleConsumedError,
                     HandleSpaceExhaustedError, HostFailure, InvalidArgument, Invalidated,
                     MemoryExhausted, NotReady, RngUnavailable, WaitSetTooLargeError, WaitTimeout)
from .lifecycle import RESOLVED, TERMINAL, State, check
from .telemetry import AuditChain, EventLog, Metrics, TraceContext

_NO_IMMEDIATE = object()
ROW_BYTES = 256          # declared accounting unit per live row (not an allocator measurement)
TOMBSTONE_BYTES = 64     # declared accounting unit per tombstone
MAX_DEADLINE_NS = (1 << 63) - 1
MAX_TREE_DEPTH = 64
PRIORITY_CLASSES = ("low", "default", "high")


@dataclass
class Limits:
    """Hierarchical ceilings. Precedence when several are exhausted:
    instance -> workload -> tenant -> process (the first exhausted scope in
    this order is reported). ``node``/``global`` scopes are outside a single
    process and are represented by the ``process`` scope in this reference."""

    instance: int = 64
    workload: int = 256
    tenant: int = 512
    process: int = 4096
    tenant_share: float = 0.5          # fairness: a tenant may hold at most this share of process
    mem_instance: int = 1 << 20
    mem_tenant: int = 8 << 20
    mem_process: int = 64 << 20
    mem_soft_ratio: float = 0.8
    tombstones: int = 1024
    waiters_per_instance: int = 1024
    idempotency_window: int = 1024

    def validate(self):
        for k in ("instance", "workload", "tenant", "process", "mem_instance", "mem_tenant",
                  "mem_process", "tombstones", "waiters_per_instance", "idempotency_window"):
            v = getattr(self, k)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise InvalidArgument(f"limit {k} must be a positive integer")
        if not 0 < self.tenant_share <= 1 or not 0 < self.mem_soft_ratio <= 1:
            raise InvalidArgument("ratios must be in (0, 1]")


@dataclass(eq=False)
class _Row:
    slot: int
    generation: int
    token: bytes
    view: "InstanceView"
    created_ns: int
    deadline_ns: int | None
    deadline_inherited: bool
    parent: "_Row | None"
    detached: bool
    cancellable: bool
    idem_key: str | None
    trace: TraceContext | None
    priority: str
    state: State = State.PENDING
    value: Any = None
    release: Callable | None = None
    payload_bytes: int = 0
    error: dict | None = None
    ready_ns: int | None = None
    children: set = field(default_factory=set)
    waiters: list = field(default_factory=list)

    def handle(self, epoch):
        return H.Handle(epoch, self.slot, self.generation, self.token)


class Subscription:
    """One-shot readiness subscription. ``cancel()`` races safely with firing."""

    def __init__(self, host, view, rows, callback):
        self._host, self.view, self._rows, self._cb = host, view, rows, callback
        self.fired = False
        self.cancelled = False
        self.result = None

    def cancel(self) -> bool:
        with self._host._lock:
            if self.fired or self.cancelled:
                return False
            self.cancelled = True
            self._host._drop_waiter(self)
            return True


class InstanceView:
    """Guest-facing binding of one component instance to its tenant/workload.

    Tenant identity binding is host-enforced: every guest operation goes through
    a view, and a handle is only accepted by the view that minted it.
    """

    def __init__(self, host, name, tenant, workload, budget):
        self._host, self.name, self.tenant, self.workload, self.budget = host, name, tenant, workload, budget
        self.state = "accepting"   # accepting -> draining -> drained | torn_down
        self.live: set[_Row] = set()
        self.idem_live: dict[str, _Row] = {}
        self.idem_done: OrderedDict[str, str] = OrderedDict()
        self.waiters = 0
        self.stats = {"calls": 0, "immediate": 0, "refusals": {}, "cancellations": {}, "abandoned": 0,
                      "consumed": 0, "trapped": 0, "timed_out": 0, "invalidated": 0,
                      "dedup_hits": 0, "late_completions": 0}
        self.drain_started_ns = None

    # guest API -------------------------------------------------------------
    def call(self, immediate=_NO_IMMEDIATE, **kw):
        return self._host._call(self, immediate, **kw)

    def wait(self, handles: Iterable[H.Handle]):
        return self._host._wait(self, handles)

    def wait_blocking(self, handles, timeout_ns: int):
        return self._host._wait_blocking(self, handles, timeout_ns)

    def subscribe(self, handles, callback):
        return self._host._subscribe(self, handles, callback)

    def take(self, handle):
        return self._host._take(self, handle)

    def cancel(self, handle, reason: CancelReason = CancelReason.CALLER_REQUESTED) -> CancelAck:
        return self._host._cancel(self, handle, reason)

    def cancel_all(self, reason: CancelReason = CancelReason.CALLER_GONE) -> int:
        return self._host._cancel_all(self, reason)

    def serialize(self, handle) -> bytes:
        return self._host._serialize(self, handle)

    def deserialize(self, data: bytes) -> H.Handle:
        return self._host._deserialize(self, data)


class AsyncHost:
    def __init__(self, limits: Limits | None = None, *, clock: Callable[[], int] | None = None,
                 token_source: Callable[[int], bytes] | None = None, epoch: int = 1,
                 max_slots: int | None = None, max_generation: int = H.U32,
                 event_sample_rate: float = 1.0, auth_key: bytes | None = None):
        self.limits = limits or Limits()
        self.limits.validate()
        self._clock = clock or time.monotonic_ns
        self._last_ns = 0
        self.clock_regressions = 0
        self._token_source = token_source or secrets.token_bytes
        self.epoch = epoch
        self._lock = threading.RLock()
        self._cond = threading.Condition(self._lock)
        self._max_slots = max_slots or self.limits.process
        self._max_generation = max_generation
        self._slots: list[_Row | None] = []
        self._gens: list[int] = []
        self._free: deque[int] = deque()
        self._retired_slots = 0
        self._tokens: dict[bytes, _Row] = {}
        self._tomb: OrderedDict[tuple, tuple] = OrderedDict()
        self._deadlines: list = []
        self._ready: dict[str, deque] = {}
        self._rr: deque[str] = deque()
        self.views: dict[str, InstanceView] = {}
        self._use = {"workload": {}, "tenant": {}, "process": 0}
        self._mem = {"instance": {}, "tenant": {}, "process": 0}
        self.disabled = False
        self.on_ready: list[Callable] = []
        self.metrics = Metrics()
        self.events = EventLog(sample_rate=event_sample_rate)
        self.audit = AuditChain()
        self._redact_key = secrets.token_bytes(32)
        self._auth_key = auth_key or secrets.token_bytes(32)
        self._last_token = b""
        self.release_errors = 0

    # time ------------------------------------------------------------------
    def now(self) -> int:
        try:
            t = int(self._clock())
        except Exception as exc:  # clock failure is a host failure, never a silent zero
            raise HostFailure("clock unavailable") from exc
        if t < self._last_ns:
            self.clock_regressions += 1
            return self._last_ns
        self._last_ns = t
        return t

    # registration ------------------------------------------------------------
    def register(self, name: str, *, tenant: str, workload: str, budget: int | None = None) -> InstanceView:
        for label, v in (("name", name), ("tenant", tenant), ("workload", workload)):
            if not isinstance(v, str) or not v or len(v) > 64 or not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
                raise InvalidArgument(f"{label} must be 1-64 chars [A-Za-z0-9._-]")
        budget = self.limits.instance if budget is None else budget
        if isinstance(budget, bool) or not isinstance(budget, int) or not 1 <= budget <= self.limits.instance:
            raise InvalidArgument("instance budget must be in 1..limits.instance")
        with self._lock:
            if name in self.views and self.views[name].state not in ("torn_down",):
                raise InvalidArgument("instance already registered")
            v = InstanceView(self, name, tenant, workload, budget)
            self.views[name] = v
            return v

    # helpers ---------------------------------------------------------------
    def _corr(self, row) -> str:
        return hmac.new(self._redact_key, row.token, hashlib.sha256).hexdigest()[:16]

    def _event(self, op, view=None, row=None, **kw):
        tr = row.trace if row is not None else None
        self.events.emit(ts_ns=self._last_ns, op=op, instance=view.name if view else None,
                         tenant=view.tenant if view else None, workload=view.workload if view else None,
                         corr=self._corr(row) if row is not None else None,
                         trace_id=tr.trace_id if tr else None, span_id=tr.span_id if tr else None, **kw)
        self.metrics.inc("pk_async_events_total", {"op": op})

    def _refuse(self, view, scope, exc):
        view.stats["refusals"][scope] = view.stats["refusals"].get(scope, 0) + 1
        self.metrics.inc("pk_async_refusals_total", {"scope": scope})
        if scope in ("instance", "workload", "tenant", "process", "fairness"):
            self.audit.append("budget_refusal", instance=view.name, scope=scope)
            self._event("budget_refusal", view, code=int(exc.code))
        raise exc

    def _payload_size(self, value, declared):
        if declared is not None:
            if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
                raise InvalidArgument("payload_bytes must be a non-negative int")
            return declared
        if value is None:
            return 0
        if isinstance(value, (bytes, str)):
            return len(value)
        return sys.getsizeof(value)

    def _mem_charge(self, view, n):
        L = self.limits
        mi = self._mem["instance"].get(view.name, 0)
        mt = self._mem["tenant"].get(view.tenant, 0)
        if mi + n > L.mem_instance or mt + n > L.mem_tenant or self._mem["process"] + n > L.mem_process:
            self.metrics.inc("pk_async_memory_refusals_total")
            raise MemoryExhausted("memory ceiling reached")
        self._mem["instance"][view.name] = mi + n
        self._mem["tenant"][view.tenant] = mt + n
        self._mem["process"] += n
        if self._mem["process"] > L.mem_process * L.mem_soft_ratio:
            self.metrics.inc("pk_async_memory_soft_limit_total")

    def _mem_release(self, view, n):
        self._mem["instance"][view.name] -= n
        self._mem["tenant"][view.tenant] -= n
        self._mem["process"] -= n

    def _budget_reserve(self, view):
        L = self.limits
        w = self._use["workload"].get(view.workload, 0)
        t = self._use["tenant"].get(view.tenant, 0)
        p = self._use["process"]
        tenant_fair_cap = max(1, int(L.process * L.tenant_share))
        if len(view.live) >= view.budget:
            self._refuse(view, "instance", BudgetExhaustedError("instance budget exhausted"))
        if w >= L.workload:
            self._refuse(view, "workload", BudgetExhaustedError("workload budget exhausted"))
        if t >= L.tenant:
            self._refuse(view, "tenant", BudgetExhaustedError("tenant budget exhausted"))
        if p >= L.process:
            self._refuse(view, "process", BudgetExhaustedError("process budget exhausted"))
        if t >= tenant_fair_cap:
            self._refuse(view, "fairness", BudgetExhaustedError("tenant fair-share exhausted"))
        self._use["workload"][view.workload] = w + 1
        self._use["tenant"][view.tenant] = t + 1
        self._use["process"] = p + 1

    def _budget_release(self, view):
        self._use["workload"][view.workload] -= 1
        self._use["tenant"][view.tenant] -= 1
        self._use["process"] -= 1

    def _new_token(self):
        try:
            tok = self._token_source(16)
        except Exception as exc:
            raise RngUnavailable("secure randomness unavailable") from exc
        if not isinstance(tok, (bytes, bytearray)) or len(tok) != 16:
            raise RngUnavailable("token source returned wrong length")
        tok = bytes(tok)
        if tok == bytes(16) or tok == self._last_token or tok in self._tokens:
            raise RngUnavailable("token source failed a health check (zero/repeat/collision)")
        self._last_token = tok
        return tok

    def _alloc_slot(self):
        if self._free:
            return self._free.popleft()
        if len(self._slots) >= self._max_slots:
            raise HandleSpaceExhaustedError("no free slot")
        self._slots.append(None)
        self._gens.append(0)
        return len(self._slots) - 1

    def _free_slot(self, slot):
        # poison: the row is gone and the generation moves, so a late producer
        # holding (slot, old generation) can never address the next occupant.
        self._slots[slot] = None
        if self._gens[slot] >= self._max_generation:
            self._retired_slots += 1   # generation wrap: slot is retired, never reused
            return
        self._gens[slot] += 1
        self._free.append(slot)

    # guest operations ------------------------------------------------------------
    def _admission_check(self, view):
        if self.disabled:
            self._refuse(view, "disabled", Disabled("host emergency-disabled"))
        if view.state == "torn_down":
            raise Invalidated("instance torn down")
        if view.state in ("draining", "drained"):
            self._refuse(view, "draining", Draining("instance is draining"))

    def _call(self, view, immediate, *, deadline_ns=None, timeout_ns=None, parent=None, detached=False,
              idempotency_key=None, trace=None, priority="default", cancellable=True):
        with self._lock:
            self._admission_check(view)
            view.stats["calls"] += 1
            if immediate is not _NO_IMMEDIATE:
                view.stats["immediate"] += 1
                self.metrics.inc("pk_async_calls_total", {"kind": "immediate"})
                return ("value", immediate)
            if priority not in PRIORITY_CLASSES:
                raise InvalidArgument("priority hint must be low|default|high")
            if idempotency_key is not None:
                if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
                    raise InvalidArgument("idempotency key must be 1-128 chars")
                live = view.idem_live.get(idempotency_key)
                if live is not None:
                    view.stats["dedup_hits"] += 1
                    self.metrics.inc("pk_async_idempotent_dedup_total")
                    return ("subtask", live.handle(self.epoch))
                if idempotency_key in view.idem_done:
                    raise HandleConsumedError(f"idempotency key already resolved as {view.idem_done[idempotency_key]}")
            now = self.now()
            dl, inherited = None, False
            for v in (deadline_ns, timeout_ns):
                if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
                    raise InvalidArgument("deadline/timeout must be non-negative int ns")
            if timeout_ns is not None:
                if now + timeout_ns > MAX_DEADLINE_NS:
                    raise InvalidArgument("timeout overflows the monotonic domain")
                dl = now + timeout_ns
            if deadline_ns is not None:
                if deadline_ns > MAX_DEADLINE_NS:
                    raise InvalidArgument("deadline overflows the monotonic domain")
                dl = deadline_ns if dl is None else min(dl, deadline_ns)
            prow = None
            if parent is not None:
                prow = self._lookup(view, parent, "call-parent")
                if prow.state is not State.PENDING:
                    raise InvalidArgument("parent must be pending")
                depth, a = 1, prow
                while a.parent is not None:
                    depth, a = depth + 1, a.parent
                if depth >= MAX_TREE_DEPTH:
                    raise InvalidArgument("cancellation tree too deep")
                if prow.deadline_ns is not None and (dl is None or prow.deadline_ns < dl):
                    dl, inherited = prow.deadline_ns, True
            if dl is not None and dl <= now:
                raise DeadlineExceeded("deadline already expired at admission")
            self._budget_reserve(view)
            try:
                self._mem_charge(view, ROW_BYTES)
            except AbiError:
                self._budget_release(view)
                view.stats["refusals"]["memory"] = view.stats["refusals"].get("memory", 0) + 1
                raise
            try:
                tok = self._new_token()
                slot = self._alloc_slot()
            except AbiError as exc:
                self._mem_release(view, ROW_BYTES)
                self._budget_release(view)
                self.audit.append("admission_failure", instance=view.name, code=int(exc.code))
                raise
            row = _Row(slot, self._gens[slot], tok, view, now, dl, inherited, prow, bool(detached),
                       bool(cancellable), idempotency_key, trace.child() if trace else None, priority)
            self._slots[slot] = row
            self._tokens[tok] = row
            view.live.add(row)
            if prow is not None:
                prow.children.add(row)
            if idempotency_key is not None:
                view.idem_live[idempotency_key] = row
            if dl is not None:
                heapq.heappush(self._deadlines, (dl, slot, row.generation))
            self.metrics.inc("pk_async_calls_total", {"kind": "subtask"})
            self._event("call", view, row, to=State.PENDING.value)
            return ("subtask", row.handle(self.epoch))

    def _foreign(self, view, handle, why):
        self.audit.append("foreign_handle", instance=view.name if view else None, why=why)
        self._event("foreign_handle", view, reason=why)
        self.metrics.inc("pk_async_foreign_handle_total")
        raise ForeignHandleError("unknown handle")  # uniform: no existence oracle

    def _lookup(self, view, handle, op, *, allow_tomb=False):
        if not isinstance(handle, H.Handle):
            self._foreign(view, handle, "type")
        if handle.epoch != self.epoch:
            raise Invalidated("handle from a previous host epoch")
        row = self._slots[handle.slot] if handle.slot < len(self._slots) else None
        if row is None or row.generation != handle.generation or not hmac.compare_digest(row.token, handle.token):
            tomb = self._tomb.get((handle.slot, handle.generation))
            if tomb and hmac.compare_digest(tomb[0], hashlib.sha256(handle.token).digest()) and tomb[1] == view.name:
                if allow_tomb:
                    return tomb
                self.audit.append("use_after_consume", instance=view.name, op=op)
                self._event("use_after_consume", view, reason=op)
                if tomb[2] == State.INVALIDATED.value:
                    raise Invalidated("handle invalidated")
                raise HandleConsumedError("handle already retired")
            self._foreign(view, handle, "unknown")
        if row.view is not view:
            self.audit.append("tenant_mismatch", instance=view.name)
            self._foreign(view, handle, "scope")
        return row

    def _set_state(self, row, dst, *, reason=None, code=None):
        src = row.state
        check(src, dst)
        row.state = dst
        self._event("transition", row.view, row, **{"from": src.value}, to=dst.value, reason=reason,
                    code=code, duration_ns=self._last_ns - row.created_ns)

    def _retire(self, row, final: State, pending_release: list):
        view = row.view
        self._set_state(row, final)
        self._slots_release(row, pending_release)
        self._tomb[(row.slot, row.generation)] = (hashlib.sha256(row.token).digest(), view.name, final.value)
        while len(self._tomb) > self.limits.tombstones:
            self._tomb.popitem(last=False)
        self._free_slot(row.slot)

    def _slots_release(self, row, pending_release):
        view = row.view
        view.live.discard(row)
        self._tokens.pop(row.token, None)
        if row.idem_key is not None:
            view.idem_live.pop(row.idem_key, None)
            view.idem_done[row.idem_key] = row.state.value
            while len(view.idem_done) > self.limits.idempotency_window:
                view.idem_done.popitem(last=False)
        if row.parent is not None:
            row.parent.children.discard(row)
        self._budget_release(view)
        self._mem_release(view, ROW_BYTES + row.payload_bytes)
        if row.release is not None and row.state is not State.CONSUMED:
            pending_release.append((row.release, row.value))
        row.value = None
        row.release = None
        for sub in list(row.waiters):
            self._fire(sub, invalidated=row.state is State.INVALIDATED, pending=pending_release)
        row.waiters.clear()

    def _run_released(self, pending):
        for fn, val in pending:
            if fn == "__sub__":
                sub = val
                try:
                    sub._cb(sub)
                except Exception:
                    self.release_errors += 1
                continue
            try:
                fn(val)
            except Exception:
                self.release_errors += 1
                self.audit.append("release_error")

    def _wait_rows(self, view, handles):
        try:
            it = iter(handles)
        except TypeError:
            raise InvalidArgument("wait set is not iterable") from None
        req = []
        for h in it:  # consumed outside the lock, exactly once, bounded
            if len(req) >= view.budget:
                raise WaitSetTooLargeError("wait set exceeds instance budget")
            req.append(h)
        return req

    def _wait(self, view, handles):
        req = self._wait_rows(view, handles)
        with self._lock:
            self.metrics.hist["wait_size"].observe(len(req))
            seen, ready = set(), []
            for h in req:
                row = self._lookup(view, h, "wait")
                if row.slot in seen:
                    continue
                seen.add(row.slot)
                if row.state in RESOLVED:
                    ready.append(h)
            return ready

    def _wait_blocking(self, view, handles, timeout_ns):
        """Host-thread wait. A wait timeout never changes subtask state."""
        req = self._wait_rows(view, handles)
        if isinstance(timeout_ns, bool) or not isinstance(timeout_ns, int) or timeout_ns < 0:
            raise InvalidArgument("timeout_ns must be a non-negative int")
        end = time.monotonic() + timeout_ns / 1e9
        with self._cond:
            while True:
                if view.state == "torn_down":
                    raise Invalidated("instance torn down while waiting")
                rows = [self._lookup(view, h, "wait") for h in req]
                ready = [h for h, r in zip(req, rows) if r.state in RESOLVED]
                if ready:
                    return ready
                left = end - time.monotonic()
                if left <= 0:
                    self.metrics.inc("pk_async_wait_timeouts_total")
                    raise WaitTimeout("wait timed out; handles remain live")
                self._cond.wait(left)

    def _subscribe(self, view, handles, callback):
        req = self._wait_rows(view, handles)
        pending = []
        with self._lock:
            rows = []
            for h in req:
                r = self._lookup(view, h, "subscribe")
                if r not in rows:
                    rows.append(r)
            if view.waiters + 1 > self.limits.waiters_per_instance:
                raise BudgetExhaustedError("waiter quota exhausted")
            sub = Subscription(self, view, rows, callback)
            view.waiters += 1
            for r in rows:           # 1. subscribe ...
                r.waiters.append(sub)
            for r in rows:           # 2. ... then re-check in the same critical section
                if r.state in RESOLVED:
                    self._fire(sub, pending=pending)
                    break
        self._run_released(pending)
        return sub

    def _drop_waiter(self, sub):
        for r in sub._rows:
            if sub in r.waiters:
                r.waiters.remove(sub)
        sub.view.waiters -= 1

    def _fire(self, sub, invalidated=False, pending=None):
        if sub.fired or sub.cancelled:
            return
        sub.fired = True
        sub.result = "invalidated" if invalidated else "ready"
        self._drop_waiter(sub)
        pending.append(("__sub__", sub))

    def _take(self, view, handle):
        pending = []
        try:
            with self._lock:
                row = self._lookup(view, handle, "take")
                if row.state is State.PENDING:
                    raise NotReady("subtask not ready")
                now = self.now()
                if row.ready_ns is not None:
                    self.metrics.hist["ready_to_take_ns"].observe(now - row.ready_ns)
                st, val, err = row.state, row.value, row.error
                if st is State.READY:
                    row.release = None  # ownership transfers to the caller
                    view.stats["consumed"] += 1
                self._retire(row, State.CONSUMED, pending)
                if st is State.READY:
                    return val
                if st is State.TRAPPED:
                    raise CalleeTrapped(err.get("detail", ""))
                if err and err.get("code") == int(ErrorCode.DEADLINE_EXCEEDED):
                    raise DeadlineExceeded("inherited deadline expired")
                raise CallTimeout("call timed out")
        finally:
            self._run_released(pending)

    def _cancel_tree(self, row, reason, pending, now):
        # iterative depth-first: children first, then the parent. Detached
        # children are re-owned by the instance and keep running.
        stack, order = [row], []
        while stack:
            r = stack.pop()
            order.append(r)
            for c in list(r.children):
                if c.detached:
                    r.children.discard(c)
                    c.parent = None
                elif c.state is State.PENDING and c.cancellable:
                    stack.append(c)
        n = 0
        for r in reversed(order):
            if r.state is not State.PENDING:
                continue
            rr = reason if r is row else CancelReason.PARENT_CANCELLED
            v = r.view
            v.stats["cancellations"][rr.name] = v.stats["cancellations"].get(rr.name, 0) + 1
            self.metrics.inc("pk_async_cancellations_total", {"reason": rr.name})
            self._retire(r, State.CANCELLED, pending)
            n += 1
        self.metrics.hist["cancel_terminal_ns"].observe(self.now() - now)
        return n

    def _cancel(self, view, handle, reason):
        if not isinstance(reason, CancelReason):
            raise InvalidArgument("reason must be a CancelReason code")
        pending = []
        try:
            with self._lock:
                t0 = self.now()
                row = self._lookup(view, handle, "cancel", allow_tomb=True)
                if isinstance(row, tuple):
                    ack = CancelAck.ALREADY_TERMINAL
                elif row.state is State.PENDING and not row.cancellable:
                    ack = CancelAck.UNABLE_TO_CANCEL
                elif row.state is State.PENDING:
                    self._cancel_tree(row, reason, pending, t0)
                    ack = CancelAck.PROPAGATED
                else:
                    view.stats["abandoned"] += 1
                    self._retire(row, State.ABANDONED, pending)
                    ack = CancelAck.COMPLETED_BEFORE_CANCEL
                self.metrics.hist["cancel_ack_ns"].observe(self.now() - t0)
                self.metrics.inc("pk_async_cancel_acks_total", {"ack": ack.name})
                return ack
        finally:
            self._run_released(pending)

    def _cancel_all(self, view, reason):
        pending = []
        try:
            with self._lock:
                t0 = self.now()
                n = 0
                for row in sorted(view.live, key=lambda r: r.slot):
                    if row.view is not view or row.state in TERMINAL or row not in view.live:
                        continue
                    if row.state is State.PENDING:
                        if not row.cancellable:
                            continue
                        n += self._cancel_tree(row, reason, pending, t0)
                    else:
                        view.stats["abandoned"] += 1
                        self._retire(row, State.ABANDONED, pending)
                if n > 32:
                    self.audit.append("cancel_storm", instance=view.name, n=n)
                return n
        finally:
            self._run_released(pending)

    # producer (host-side) API -------------------------------------------------------
    def _producer_row(self, handle):
        if not isinstance(handle, H.Handle) or handle.epoch != self.epoch:
            return None
        row = self._slots[handle.slot] if handle.slot < len(self._slots) else None
        if row is None or row.generation != handle.generation or not hmac.compare_digest(row.token, handle.token):
            return None
        return row

    def _publish(self, handle, dst, *, value=None, release=None, payload_bytes=None, error=None):
        pending, notify = [], None
        try:
            with self._lock:
                row = self._producer_row(handle)
                if row is None:
                    # late completion after cancel/teardown/restart/slot reuse: discarded,
                    # accounted, and the producer's payload is released by the host.
                    self.metrics.inc("pk_async_late_completions_total")
                    self.audit.append("late_completion")
                    self._event("late_completion")
                    if release is not None:
                        pending.append((release, value))
                    return "discarded_late"
                if row.state is not State.PENDING:
                    self.audit.append("duplicate_publication", instance=row.view.name)
                    self._event("duplicate_publication", row.view, row)
                    raise DuplicatePublication("subtask already resolved; first result kept")
                ready_ns = self.now()  # timestamp first: a clock failure must not leave a partial publication
                if dst is State.READY:
                    if isinstance(value, (bytearray, memoryview)):
                        value = bytes(value)  # mutable buffers are copied: zero-copy only for immutable bytes
                    n = self._payload_size(value, payload_bytes)
                    self._mem_charge(row.view, n)  # may raise MemoryExhausted; row stays PENDING
                    row.payload_bytes = n
                    row.value, row.release = value, release
                else:
                    row.error = error
                    if release is not None:
                        pending.append((release, value))
                row.ready_ns = ready_ns
                self._set_state(row, dst, code=error.get("code") if error else None)
                if dst is State.TRAPPED:
                    row.view.stats["trapped"] += 1
                if dst is State.TIMED_OUT:
                    row.view.stats["timed_out"] += 1
                q = self._ready.setdefault(row.view.tenant, deque())
                if not q:
                    self._rr.append(row.view.tenant)
                q.append((row, row.generation))
                if len(q) > 2 * self._use["tenant"].get(row.view.tenant, 0) + 64:
                    # compaction: entries for rows retired without passing through
                    # ready_batch are dropped, so the queue stays O(live rows)
                    live = [(r, g) for r, g in q if self._slots[r.slot] is r and r.generation == g
                            and r.state in RESOLVED]
                    q.clear()
                    q.extend(live)
                for sub in list(row.waiters):
                    self._fire(sub, pending=pending)
                self._cond.notify_all()
                notify = (row.view.name, row.ready_ns)
                return "published"
        finally:
            self._run_released(pending)
            if notify:
                for hook in list(self.on_ready):
                    hook(*notify)

    def complete(self, handle, value, *, release=None, payload_bytes=None):
        return self._publish(handle, State.READY, value=value, release=release, payload_bytes=payload_bytes)

    def trap(self, handle, detail="callee trapped", *, code=ErrorCode.TRAPPED):
        return self._publish(handle, State.TRAPPED, error={"code": int(code), "detail": str(detail)[:256]})

    def expire(self) -> int:
        """Resolve every pending subtask whose deadline has passed (O(k log n))."""
        n = 0
        now = self.now()
        while True:
            with self._lock:
                if not self._deadlines or self._deadlines[0][0] > now:
                    return n
                dl, slot, gen = heapq.heappop(self._deadlines)
                row = self._slots[slot]
                if row is None or row.generation != gen or row.state is not State.PENDING:
                    continue
                code = ErrorCode.DEADLINE_EXCEEDED if row.deadline_inherited else ErrorCode.CALL_TIMEOUT
                h = row.handle(self.epoch)
            if self._publish(h, State.TIMED_OUT, error={"code": int(code), "detail": "deadline"}) == "published":
                n += 1

    def ready_batch(self, max_n: int = 64):
        """Bounded, tenant-round-robin batch of resolved subtasks (lazy deletion)."""
        if isinstance(max_n, bool) or not isinstance(max_n, int) or not 1 <= max_n <= 4096:
            raise InvalidArgument("max_n must be in 1..4096")
        out = []
        with self._lock:
            idle = 0
            while len(out) < max_n and self._rr and idle < len(self._rr):
                tenant = self._rr[0]
                q = self._ready.get(tenant)
                self._rr.rotate(-1)
                while q:
                    row, gen = q.popleft()
                    if self._slots[row.slot] is row and row.generation == gen and row.state in RESOLVED:
                        out.append((row.view.name, row.handle(self.epoch)))
                        idle = 0
                        break
                else:
                    idle += 1
                if not q:
                    self._ready.pop(tenant, None)
                    if tenant in self._rr:
                        self._rr.remove(tenant)
                    idle = 0
        return out

    # drain / disable / teardown / restart ------------------------------------------
    def drain(self, view, policy="allow"):
        if policy not in ("allow", "cancel", "invalidate"):
            raise InvalidArgument("policy must be allow|cancel|invalidate")
        with self._lock:
            if view.state == "accepting":
                view.state = "draining"
                view.drain_started_ns = self.now()
        if policy == "cancel":
            self._cancel_all(view, CancelReason.DRAIN)
        elif policy == "invalidate":
            self.teardown(view)
        return self.drain_progress(view)

    def drain_progress(self, view):
        with self._lock:
            now = self.now()
            live = len(view.live)
            if view.state == "draining" and live == 0:
                view.state = "drained"
            oldest = min((r.created_ns for r in view.live), default=None)
            return {"instance": view.name, "state": view.state, "live": live,
                    "pending": sum(1 for r in view.live if r.state is State.PENDING),
                    "oldest_age_ns": None if oldest is None else now - oldest,
                    "cancellations": dict(view.stats["cancellations"]),
                    "blockers": sorted({"uncancellable" for r in view.live if not r.cancellable})}

    def resume_admission(self, view):
        with self._lock:
            if view.state in ("draining", "drained"):
                view.state = "accepting"

    def disable(self):
        """Emergency kill switch: refuse all admission, cancel all pending work."""
        with self._lock:
            self.disabled = True
            views = list(self.views.values())
        self.audit.append("emergency_disable")
        for v in views:
            if v.state != "torn_down":
                self._cancel_all(v, CancelReason.EMERGENCY_DISABLE)

    def enable(self):
        with self._lock:
            self.disabled = False
        self.audit.append("emergency_enable")

    def teardown(self, view):
        pending = []
        try:
            with self._lock:
                for row in sorted(view.live, key=lambda r: r.slot):
                    view.stats["invalidated"] += 1
                    self._retire(row, State.INVALIDATED, pending)
                view.state = "torn_down"
                view.idem_live.clear()
                self._cond.notify_all()
        finally:
            self._run_released(pending)

    def restart(self):
        """Model a host process restart: new epoch, every live handle invalidated."""
        for v in list(self.views.values()):
            self.teardown(v)
        with self._lock:
            self.epoch = (self.epoch + 1) & H.U32 or 1
            self._tomb.clear()
            self._ready.clear()
            self._rr.clear()
            self._deadlines.clear()
            self.views.clear()

    # serialization across boundaries -------------------------------------------------
    def _serialize(self, view, handle):
        with self._lock:
            self._lookup(view, handle, "serialize")
            return H.encode(handle, auth_key=self._auth_key, tenant=f"{view.tenant}/{view.name}")

    def _deserialize(self, view, data):
        try:
            h = H.decode(data, auth_key=self._auth_key, tenant=f"{view.tenant}/{view.name}")
        except AbiError as exc:
            self.audit.append("replay", instance=view.name, code=int(exc.code))
            self._event("replay", view, code=int(exc.code))
            raise
        with self._lock:
            self._lookup(view, h, "deserialize")
        return h

    # operator views -----------------------------------------------------------------
    def explain(self, max_instances: int = 64) -> dict:
        """Bounded operator view. Contains no tokens, payloads or correlation ids."""
        with self._lock:
            inst = []
            for v in sorted(self.views.values(), key=lambda v: v.name)[:max_instances]:
                by_state = {}
                for r in v.live:
                    by_state[r.state.value] = by_state.get(r.state.value, 0) + 1
                inst.append({"instance": v.name, "tenant": v.tenant, "workload": v.workload,
                             "state": v.state, "live": len(v.live), "budget": v.budget,
                             "by_state": by_state, "refusals": dict(v.stats["refusals"]),
                             "memory_bytes": self._mem["instance"].get(v.name, 0),
                             "waiters": v.waiters})
            return {"epoch": self.epoch, "disabled": self.disabled,
                    "instances": inst, "instances_truncated": max(0, len(self.views) - max_instances),
                    "process": {"live": self._use["process"], "limit": self.limits.process,
                                "memory_bytes": self._mem["process"], "memory_limit": self.limits.mem_process,
                                "tombstones": len(self._tomb), "slots": len(self._slots),
                                "retired_slots": self._retired_slots,
                                "clock_regressions": self.clock_regressions,
                                "release_errors": self.release_errors},
                    "dependencies": {"scheduler_hooks": len(self.on_ready),
                                     "audit_chain": self.audit.verify()[0]}}

    def refresh_gauges(self):
        with self._lock:
            for v in self.views.values():
                self.metrics.set("pk_async_subtasks_open", len(v.live), {"instance": v.name})
                self.metrics.set("pk_async_subtasks_ready",
                                 sum(1 for r in v.live if r.state in RESOLVED), {"instance": v.name})
                self.metrics.set("pk_async_memory_bytes", self._mem["instance"].get(v.name, 0), {"instance": v.name})
            self.metrics.set("pk_async_tombstones", len(self._tomb))
