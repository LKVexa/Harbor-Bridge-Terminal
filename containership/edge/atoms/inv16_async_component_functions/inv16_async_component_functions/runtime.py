"""Thread-safe runtime model for INV-16 async component functions (v4.3.0).

Closure items implemented here (see ``docs/CLOSURE_LEDGER.md``):

* #10  structured cancellation reasons, first-terminal-wins precedence
* #11  per-function re-entrancy policy (allow / refuse / bounded FIFO queue)
* #12  bounded terminal tombstones with "history expired" classification
* #13  finite-width call-id allocator, generation (epoch) identity, no silent reuse
* #15  explicit terminal transition table (``TRANSITIONS``) enforced atomically
* #20  deterministic fault-injection points evaluated before any mutation
* #23-25 metric snapshot, structured events and trace context, all dispatched
        *outside* the lifecycle lock so telemetry can never block a transition

Everything stays stdlib-only so the safety-critical model is testable without
``pk_core``.  Public names from 4.2.0 keep their meaning; behavioural deltas are
listed in ``CHANGELOG.md``.
"""
from __future__ import annotations

import os
import re
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, Mapping

RUNTIME_SCHEMA = "PK_ASYNC_INVOKE/1"
EVENT_SCHEMA = "inv16.event/1"

# --------------------------------------------------------------------------- errors


class ReentrancyRefused(RuntimeError):
    """Raised when re-entering an instance would corrupt an in-flight call."""


class ReentrancyQueueFull(ReentrancyRefused):
    """Raised when a queued re-entrancy policy has no queue slot left."""


class ConcurrencyLimitReached(RuntimeError):
    """Raised when the configured per-instance in-flight budget is exhausted."""


class TerminalConflict(RuntimeError):
    """Base class: an operation lost the race for a call's single terminal transition."""

    def __init__(self, message: str, tombstone: "Tombstone | None" = None):
        super().__init__(message)
        self.tombstone = tombstone


class DoubleDelivery(TerminalConflict):
    """Raised if a completed call receives a second completion value."""


class CallCancelled(TerminalConflict):
    """Raised if a value is delivered after the call has been cancelled."""


class CallTrapped(TerminalConflict):
    """Raised if a value is delivered after the callee trapped."""


class AlreadyTerminal(TerminalConflict):
    """Raised when cancel/trap targets a call that already has a terminal outcome."""


class HistoryExpired(ValueError):
    """The call id was issued, but its tombstone has been reclaimed (bounded history)."""


class StaleGeneration(ValueError):
    """The call id belongs to a previous generation (epoch) of this instance."""


class CallNotStarted(ValueError):
    """Completion was delivered for a call that is still queued for admission."""


class CallIdExhausted(RuntimeError):
    """The finite ABI call-id space for this generation is used up."""


class FaultInjected(RuntimeError):
    """Raised by test fault injectors; never raised by production code paths."""


# --------------------------------------------------------------------------- value types


class Outcome(str, Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TRAPPED = "trapped"


class CancelCode(str, Enum):
    """Canonical, versioned cancellation codes (metrics/alerts key on these)."""

    CALLER = "caller"
    DEADLINE = "deadline"
    DISCONNECT = "disconnect"
    PARENT = "parent"
    OPERATOR = "operator"
    SHUTDOWN = "shutdown"
    UNSPECIFIED = "unspecified"


CANCEL_CODE_VERSION = 1
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SECRETISH = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|authorization)\s*[=:]\s*\S+")
MAX_REASON_TEXT = 200


def sanitize_reason_text(text: object) -> str:
    """Strip control characters, redact secret-looking pairs, bound length."""
    s = _CTRL.sub(" ", str(text))
    s = _SECRETISH.sub(lambda m: m.group(1) + "=<redacted>", s)
    return s[:MAX_REASON_TEXT]


@dataclass(frozen=True, slots=True)
class CancelReason:
    code: CancelCode = CancelCode.UNSPECIFIED
    message: str = ""
    initiator: str = "unknown"
    seq: int = 0          # monotonic sequence inside the instance
    at_ns: int = 0        # time.monotonic_ns() at record time

    @staticmethod
    def coerce(reason: "CancelReason | str | None", default: CancelCode) -> "CancelReason":
        if isinstance(reason, CancelReason):
            return CancelReason(CancelCode(reason.code), sanitize_reason_text(reason.message),
                                sanitize_reason_text(reason.initiator)[:64])
        if reason is None:
            return CancelReason(default)
        text = str(reason)
        try:
            return CancelReason(CancelCode(text))
        except ValueError:
            return CancelReason(default, sanitize_reason_text(text))


@dataclass(frozen=True, slots=True)
class Tombstone:
    """Minimal terminal record kept for late/duplicate event classification."""

    outcome: Outcome
    generation: int
    reason: CancelReason | None = None


# Terminal transition contract (#15).  Key: (current state, operation) -> result.
# "live"/"queued" are non-terminal; the three outcomes are absorbing.
TRANSITIONS: Mapping[tuple[str, str], str] = MappingProxyType({
    ("live", "complete"): "-> completed",
    ("live", "cancel"): "-> cancelled",
    ("live", "trap"): "-> trapped",
    ("queued", "complete"): "raise CallNotStarted (state unchanged)",
    ("queued", "cancel"): "-> cancelled (never admitted)",
    ("queued", "trap"): "-> trapped (never admitted)",
    ("completed", "complete"): "raise DoubleDelivery (+double_delivery_attempts)",
    ("cancelled", "complete"): "raise CallCancelled",
    ("trapped", "complete"): "raise CallTrapped",
    ("completed", "cancel"): "raise AlreadyTerminal (cause preserved)",
    ("cancelled", "cancel"): "raise AlreadyTerminal (first cause preserved)",
    ("trapped", "cancel"): "raise AlreadyTerminal",
    ("completed", "trap"): "no-op (trap_all only sees live/queued calls)",
    ("cancelled", "trap"): "no-op",
    ("trapped", "trap"): "no-op",
    ("expired", "*"): "raise HistoryExpired",
    ("never-issued", "*"): "raise ValueError",
    ("other-generation", "*"): "raise StaleGeneration",
})


# --------------------------------------------------------------------------- policy


class ReentrancyMode(str, Enum):
    ALLOW = "allow"
    REFUSE = "refuse"
    QUEUE = "queue"


@dataclass(frozen=True, slots=True)
class ReentrancyPolicy:
    mode: ReentrancyMode = ReentrancyMode.ALLOW
    queue_depth: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ReentrancyMode(self.mode))
        if isinstance(self.queue_depth, bool) or not isinstance(self.queue_depth, int):
            raise TypeError("queue_depth must be int")
        if self.mode is ReentrancyMode.QUEUE and self.queue_depth < 1:
            raise ValueError("queue policy needs queue_depth >= 1")
        if self.mode is not ReentrancyMode.QUEUE and self.queue_depth != 0:
            raise ValueError("queue_depth is only valid for the queue policy")


REFUSE = ReentrancyPolicy(ReentrancyMode.REFUSE)
ALLOW = ReentrancyPolicy(ReentrancyMode.ALLOW)


# --------------------------------------------------------------------------- call ids


class CallIdAllocator:
    """Monotonic allocator for a finite ABI width.  Never wraps inside a generation.

    Id 0 is reserved (null handle).  When the space is used up allocation fails
    closed with :class:`CallIdExhausted`; the owner must drain the instance and
    call :meth:`AsyncFunctions.renew_generation`.
    """

    __slots__ = ("bits", "max_id", "next_id", "warn_at")

    def __init__(self, bits: int = 64, warn_fraction: float = 0.9):
        if isinstance(bits, bool) or not isinstance(bits, int) or not 2 <= bits <= 64:
            raise ValueError("call_id_bits must be an int in [2, 64]")
        if not 0.0 < warn_fraction <= 1.0:
            raise ValueError("warn_fraction must be in (0, 1]")
        self.bits = bits
        self.max_id = (1 << bits) - 1
        self.next_id = 1
        self.warn_at = max(1, int(self.max_id * warn_fraction))

    def allocate(self) -> int:
        if self.next_id > self.max_id:
            raise CallIdExhausted(f"{self.bits}-bit call-id space exhausted")
        cid = self.next_id
        self.next_id += 1
        return cid

    @property
    def near_exhaustion(self) -> bool:
        return self.next_id >= self.warn_at

    @property
    def remaining(self) -> int:
        return self.max_id - self.next_id + 1

    def was_issued(self, call_id: int) -> bool:
        return 1 <= call_id < self.next_id

    def encode(self, call_id: int) -> bytes:
        """Canonical little-endian encoding at the ABI width (8 bytes max)."""
        if not 1 <= call_id <= self.max_id:
            raise ValueError("call id out of range for ABI width")
        return call_id.to_bytes(8, "little")

    def decode(self, raw: bytes) -> int:
        if len(raw) != 8:
            raise ValueError("call id encoding must be 8 bytes")
        cid = int.from_bytes(raw, "little")
        if not 1 <= cid <= self.max_id:
            raise ValueError("decoded call id out of range")
        return cid


# --------------------------------------------------------------------------- trace


_HEX = re.compile(r"^[0-9a-f]+$")


@dataclass(frozen=True, slots=True)
class TraceContext:
    """W3C trace-context compatible correlation data. Never used for authorisation."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    sampled: bool = True

    @staticmethod
    def parse(traceparent: str | None) -> "TraceContext | None":
        """Parse ``00-<32hex>-<16hex>-<2hex>``; returns None when malformed."""
        if not isinstance(traceparent, str) or len(traceparent) > 64:
            return None
        parts = traceparent.strip().split("-")
        if len(parts) != 4:
            return None
        ver, tid, sid, flags = parts
        if (ver != "00" or len(tid) != 32 or len(sid) != 16 or len(flags) != 2
                or not all(_HEX.match(p) for p in (tid, sid, flags))
                or tid == "0" * 32 or sid == "0" * 16):
            return None
        return TraceContext(tid, sid, None, bool(int(flags, 16) & 1))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.span_id, self.sampled)

    @staticmethod
    def root() -> "TraceContext":
        return TraceContext(os.urandom(16).hex(), os.urandom(8).hex(), None, True)

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


# --------------------------------------------------------------------------- call state


@dataclass(slots=True)
class CallState:
    """State for one call. Never shared with another call."""

    call_id: int
    function: str
    caller_is_async: bool = True
    value: object = None
    generation: int = 0
    status: str = "live"            # "live" | "queued"
    trace: TraceContext | None = None
    started_ns: int = 0


TerminalListener = Callable[[int, Outcome, object, "CancelReason | None"], None]
EventSink = Callable[[dict], None]
FaultInjector = Callable[[str, "int | None"], None]
FAULT_POINTS = ("allocate", "admit", "publish_completion", "cancel", "trap", "promote")


# --------------------------------------------------------------------------- runtime


@dataclass
class AsyncFunctions:
    """Guest-visible async function surface for one instance.

    Declarations are frozen on construction, every lifecycle transition is
    serialised under one lock, terminal history is bounded, and telemetry /
    listener callbacks are dispatched after the lock is released.
    """

    instance: str
    declared: Mapping[str, bool] = field(default_factory=dict)
    stateful: frozenset[str] = frozenset()
    concurrency_limit: int | None = None
    reentrancy: Mapping[str, ReentrancyPolicy] = field(default_factory=dict)
    tombstone_capacity: int = 65_536
    call_id_bits: int = 64
    generation: int = 0
    require_generation: bool = False
    event_sink: EventSink | None = None
    fault_injector: FaultInjector | None = None
    transport: Any = None           # an abi.Codec, or None for in-process values
    tracing: bool = False
    descriptor_digest: str | None = None

    in_flight: dict[int, CallState] = field(default_factory=dict, init=False)
    _queued: dict[int, CallState] = field(default_factory=dict, init=False, repr=False)
    _queues: dict[str, deque] = field(default_factory=dict, init=False, repr=False)
    _active_by_fn: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _terminal: "OrderedDict[int, Tombstone]" = field(default_factory=OrderedDict, init=False, repr=False)
    _listeners: dict[int, TerminalListener] = field(default_factory=dict, init=False, repr=False)
    _ids: CallIdAllocator = field(init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _depth: int = field(default=0, init=False, repr=False)
    _outbox: list = field(default_factory=list, init=False, repr=False)
    _seq: int = field(default=0, init=False, repr=False)
    _exhaustion_warned: bool = field(default=False, init=False, repr=False)

    reentrancy_refusals: int = 0
    concurrency_refusals: int = 0
    queue_refusals: int = 0
    queued_calls: int = 0
    bridge_calls: int = 0
    double_delivery_attempts: int = 0
    completed_calls: int = 0
    cancelled_calls: int = 0
    trapped_calls: int = 0
    tombstone_evictions: int = 0
    expired_late_events: int = 0
    stale_generation_events: int = 0
    sink_failures: int = 0
    listener_failures: int = 0
    trace_context_rejected: int = 0

    # -- construction -------------------------------------------------------

    def __post_init__(self) -> None:
        if not isinstance(self.instance, str) or not self.instance:
            raise ValueError("instance must be a non-empty string")
        normalized: dict[str, bool] = {}
        for name, is_async in dict(self.declared).items():
            if not isinstance(name, str) or not name:
                raise ValueError("function names must be non-empty strings")
            if not isinstance(is_async, bool):
                raise TypeError(f"async declaration for {name!r} must be bool")
            normalized[name] = is_async
        stateful = frozenset(self.stateful)
        unknown = stateful - set(normalized)
        if unknown:
            raise ValueError(f"stateful functions must be declared: {sorted(unknown)!r}")
        if self.concurrency_limit is not None:
            if isinstance(self.concurrency_limit, bool) or not isinstance(self.concurrency_limit, int):
                raise TypeError("concurrency_limit must be an integer or None")
            if self.concurrency_limit < 1:
                raise ValueError("concurrency_limit must be >= 1")
        if isinstance(self.tombstone_capacity, bool) or not isinstance(self.tombstone_capacity, int) \
                or self.tombstone_capacity < 1:
            raise ValueError("tombstone_capacity must be a positive int")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 0:
            raise ValueError("generation must be a non-negative int")
        policies: dict[str, ReentrancyPolicy] = {}
        for name, pol in dict(self.reentrancy).items():
            if name not in normalized:
                raise ValueError(f"re-entrancy policy for undeclared function {name!r}")
            if not isinstance(pol, ReentrancyPolicy):
                raise TypeError("re-entrancy policies must be ReentrancyPolicy instances")
            policies[name] = pol
        for name in stateful:
            pol = policies.setdefault(name, REFUSE)
            if pol.mode is ReentrancyMode.ALLOW:
                raise ValueError(f"{name!r} is stateful across suspension; 'allow' would corrupt it")
        for name, pol in policies.items():
            if pol.mode is not ReentrancyMode.ALLOW:
                stateful = stateful | {name}
        self.declared = MappingProxyType(normalized)
        self.stateful = stateful
        self.reentrancy = MappingProxyType(policies)
        self._ids = CallIdAllocator(self.call_id_bits)
        object.__setattr__(self, "_sealed", True)

    _FROZEN = frozenset({"instance", "declared", "stateful", "reentrancy", "call_id_bits",
                         "descriptor_digest", "transport"})

    def __setattr__(self, name: str, value: object) -> None:
        # Build-time identity/declarations cannot be swapped after construction (threat T4).
        if name in AsyncFunctions._FROZEN and self.__dict__.get("_sealed"):
            raise AttributeError(f"{name} is fixed at build time and cannot be reassigned")
        object.__setattr__(self, name, value)

    @classmethod
    def from_descriptor(cls, instance: str, descriptor: Mapping, *, expected_digest: str | None = None,
                        **kwargs) -> "AsyncFunctions":
        """Build from an INV-11 ``PK_ASYNC_DECL/1`` descriptor (see ``declare.py``)."""
        from .declare import verify_descriptor  # local import keeps runtime stdlib-only at import
        digest = verify_descriptor(descriptor, expected_digest)
        declared = {name: meta["async"] for name, meta in descriptor["functions"].items()}
        return cls(instance, declared=declared, descriptor_digest=digest, **kwargs)

    # -- lock / dispatch ----------------------------------------------------

    def __enter__(self):
        self._lock.acquire()
        self._depth += 1
        return self

    def __exit__(self, *exc):
        self._depth -= 1
        outbox: list = []
        if self._depth == 0 and self._outbox:
            outbox, self._outbox = self._outbox, []
        self._lock.release()
        for item in outbox:  # outside the lock: telemetry/listeners can't block transitions
            kind, payload = item
            if kind == "event":
                sink = self.event_sink
                if sink is not None:
                    try:
                        sink(payload)
                    except Exception:  # noqa: BLE001 - sink failure isolation is the contract
                        with self._lock:
                            self.sink_failures += 1
            else:
                listener, args = payload
                try:
                    listener(*args)
                except Exception:  # noqa: BLE001
                    with self._lock:
                        self.listener_failures += 1
        return False

    def _event(self, etype: str, severity: str, state: CallState | None = None, **extra) -> None:
        if self.event_sink is None:
            return
        self._seq += 1
        ev = {
            "schema": EVENT_SCHEMA, "seq": self._seq, "ts_ns": time.time_ns(), "severity": severity,
            "type": etype, "instance": self.instance, "generation": self.generation,
        }
        if state is not None:
            ev["function"] = state.function
            ev["call_id"] = state.call_id
            if state.trace is not None:
                ev["trace_id"] = state.trace.trace_id
                ev["span_id"] = state.trace.span_id
        ev.update(extra)
        self._outbox.append(("event", ev))

    def _fault(self, point: str, call_id: int | None = None) -> None:
        if self.fault_injector is not None:
            self.fault_injector(point, call_id)

    # -- queries ------------------------------------------------------------

    def is_async(self, function: str) -> bool:
        try:
            return self.declared[function]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{function!r} is not declared on {self.instance}") from exc

    @property
    def calls_in_flight(self) -> int:
        with self._lock:
            return len(self.in_flight)

    @property
    def calls_queued(self) -> int:
        with self._lock:
            return len(self._queued)

    @property
    def tombstones(self) -> int:
        with self._lock:
            return len(self._terminal)

    def terminal_info(self, call_id: int, generation: int | None = None) -> Tombstone | None:
        """Safe diagnostic access to a terminal record; never resurrects a call."""
        with self._lock:
            self._check_generation(call_id, generation)
            return self._terminal.get(call_id)

    def snapshot(self) -> dict:
        with self._lock:
            per_fn: dict[str, int] = {}
            for st in self.in_flight.values():
                per_fn[st.function] = per_fn.get(st.function, 0) + 1
            return {
                "instance": self.instance, "generation": self.generation,
                "calls_in_flight": len(self.in_flight), "calls_in_flight_by_function": per_fn,
                "calls_queued": len(self._queued), "tombstones": len(self._terminal),
                "tombstone_capacity": self.tombstone_capacity,
                "call_ids_remaining": self._ids.remaining, "call_id_near_exhaustion": self._ids.near_exhaustion,
                **{k: getattr(self, k) for k in COUNTERS},
            }

    # -- invoke -------------------------------------------------------------

    def invoke(self, function: str, caller_is_async: bool = True, *,
               traceparent: str | None = None) -> CallState:
        if not isinstance(caller_is_async, bool):
            raise TypeError("caller_is_async must be bool")
        async_decl = self.is_async(function)
        with self:
            self._fault("admit")
            policy = self.reentrancy.get(function, ALLOW)
            busy = self._active_by_fn.get(function, 0) > 0 and policy.mode is not ReentrancyMode.ALLOW
            queue_it = False
            if busy:
                if policy.mode is ReentrancyMode.REFUSE:
                    self.reentrancy_refusals += 1
                    self._event("reentrancy_refused", "warn", None, function=function, reason_code="stateful_busy")
                    raise ReentrancyRefused(f"{function} holds state across suspension and is already in flight")
                q = self._queues.setdefault(function, deque())
                if len(q) >= policy.queue_depth:
                    self.queue_refusals += 1
                    self.reentrancy_refusals += 1
                    self._event("reentrancy_refused", "warn", None, function=function, reason_code="queue_full")
                    raise ReentrancyQueueFull(f"{function} re-entrancy queue full ({policy.queue_depth})")
                queue_it = True
            elif self.concurrency_limit is not None and len(self.in_flight) >= self.concurrency_limit:
                self.concurrency_refusals += 1
                self._event("concurrency_refused", "warn", None, function=function,
                            reason_code="limit", limit=self.concurrency_limit)
                raise ConcurrencyLimitReached(
                    f"{self.instance} already has {len(self.in_flight)} calls in flight "
                    f"(limit {self.concurrency_limit})")
            self._fault("allocate")
            cid = self._ids.allocate()
            trace = None
            if traceparent is not None:
                parent = TraceContext.parse(traceparent)
                if parent is None:
                    self.trace_context_rejected += 1
                    trace = TraceContext.root() if self.tracing else None
                else:
                    trace = parent.child()
            elif self.tracing:
                trace = TraceContext.root()
            state = CallState(cid, function, caller_is_async, None, self.generation,
                              "queued" if queue_it else "live", trace, time.monotonic_ns())
            if async_decl and not caller_is_async:
                self.bridge_calls += 1
            if queue_it:
                self._queues[function].append(state)
                self._queued[cid] = state
                self.queued_calls += 1
                self._event("call_queued", "info", state)
            else:
                self._admit(state)
            if self._ids.near_exhaustion and not self._exhaustion_warned:
                self._exhaustion_warned = True
                self._event("call_id_near_exhaustion", "warn", None, remaining=self._ids.remaining)
            return state

    def _admit(self, state: CallState) -> None:
        state.status = "live"
        self.in_flight[state.call_id] = state
        self._active_by_fn[state.function] = self._active_by_fn.get(state.function, 0) + 1

    def _prefault_release(self, function: str) -> None:
        """Evaluate the 'promote' fault point *before* any terminal mutation."""
        if self._active_by_fn.get(function, 0) <= 1 and self._queues.get(function):
            self._fault("promote")

    def _release_slot(self, function: str) -> None:
        n = self._active_by_fn.get(function, 0) - 1
        if n > 0:
            self._active_by_fn[function] = n
        else:
            self._active_by_fn.pop(function, None)
            q = self._queues.get(function)
            if q:
                nxt = q.popleft()
                self._queued.pop(nxt.call_id, None)
                self._admit(nxt)
                self._event("call_promoted", "info", nxt)

    # -- terminal transitions -----------------------------------------------

    def _check_generation(self, call_id: object, generation: int | None) -> None:
        if isinstance(call_id, bool) or not isinstance(call_id, int):
            raise ValueError(f"call {call_id!r} was never issued by {self.instance}")
        if generation is None:
            if self.require_generation:
                raise StaleGeneration("this instance requires an explicit generation on every call id")
            return
        if generation != self.generation:
            self.stale_generation_events += 1
            self._event("stale_generation", "warn", None, call_id=call_id, stale_generation=generation)
            raise StaleGeneration(f"call {call_id} belongs to generation {generation}, "
                                  f"instance is at {self.generation}")

    def _classify_missing(self, call_id: int, op: str) -> None:
        tomb = self._terminal.get(call_id)
        if tomb is not None:
            if op == "complete":
                if tomb.outcome is Outcome.COMPLETED:
                    self.double_delivery_attempts += 1
                    self._event("double_delivery", "critical", None, call_id=call_id)
                    raise DoubleDelivery(f"call {call_id} already delivered", tomb)
                if tomb.outcome is Outcome.CANCELLED:
                    raise CallCancelled(f"call {call_id} was cancelled", tomb)
                raise CallTrapped(f"call {call_id} ended when the callee trapped", tomb)
            raise AlreadyTerminal(f"call {call_id} already {tomb.outcome.value}", tomb)
        if self._ids.was_issued(call_id):
            self.expired_late_events += 1
            self._event("late_event_history_expired", "warn", None, call_id=call_id, op=op)
            raise HistoryExpired(f"call {call_id} was issued but its terminal history has expired")
        raise ValueError(f"call {call_id!r} was never issued by {self.instance}")

    def _bury(self, state: CallState, outcome: Outcome, reason: CancelReason | None, value: object) -> None:
        if reason is None:  # reason-less tombstones are immutable and shared: O(1) bytes each
            key = (outcome, state.generation)
            tomb = _SHARED_TOMBS.get(key)
            if tomb is None:
                tomb = _SHARED_TOMBS.setdefault(key, Tombstone(outcome, state.generation, None))
        else:
            tomb = Tombstone(outcome, state.generation, reason)
        self._terminal[state.call_id] = tomb
        while len(self._terminal) > self.tombstone_capacity:
            self._terminal.popitem(last=False)
            self.tombstone_evictions += 1
        listener = self._listeners.pop(state.call_id, None)
        if listener is not None:
            self._outbox.append(("listener", (listener, (state.call_id, outcome, value, reason))))

    def complete(self, call_id: int, value: object, *, generation: int | None = None) -> object:
        with self:
            self._check_generation(call_id, generation)
            state = self.in_flight.get(call_id)
            if state is None:
                if call_id in self._queued:
                    raise CallNotStarted(f"call {call_id} is queued and has not started")
                self._classify_missing(call_id, "complete")
            # Winner is decided before any value is touched; faults leave state intact.
            self._fault("publish_completion", call_id)
            self._prefault_release(state.function)
            if self.transport is not None:
                payload = self.transport.lower(value, call_id)       # may raise: state unchanged
                delivered = self.transport.lift(payload, call_id)
            else:
                payload = delivered = value
            del self.in_flight[call_id]
            state.value = payload
            self.completed_calls += 1
            self._bury(state, Outcome.COMPLETED, None, delivered)
            self._release_slot(state.function)
            self._event("call_completed", "debug", state, outcome="completed",
                        latency_ns=time.monotonic_ns() - state.started_ns)
            return delivered

    def cancel(self, call_id: int, reason: CancelReason | str | None = None, *,
               generation: int | None = None) -> CallState:
        with self:
            self._check_generation(call_id, generation)
            state = self.in_flight.get(call_id) or self._queued.get(call_id)
            if state is None:
                self._classify_missing(call_id, "cancel")
            self._fault("cancel", call_id)
            if state.status == "live":
                self._prefault_release(state.function)
            self._seq += 1
            r = CancelReason.coerce(reason, CancelCode.CALLER)
            r = CancelReason(r.code, r.message, r.initiator, self._seq, time.monotonic_ns())
            self._drop_nonterminal(state)
            self.cancelled_calls += 1
            self._bury(state, Outcome.CANCELLED, r, None)
            self._event("call_cancelled", "info", state, outcome="cancelled", reason_code=r.code.value)
            return state

    def _drop_nonterminal(self, state: CallState) -> None:
        if state.status == "queued":
            self._queued.pop(state.call_id, None)
            q = self._queues.get(state.function)
            if q is not None:
                try:
                    q.remove(state)
                except ValueError:  # pragma: no cover - defensive: a queued state is always enqueued
                    pass  # pragma: no cover
        else:
            del self.in_flight[state.call_id]
            self._release_slot(state.function)

    def cancel_all(self, reason: CancelReason | str | None = "caller gone") -> int:
        with self:
            self._fault("cancel")
            self._seq += 1
            r = CancelReason.coerce(reason, CancelCode.PARENT)
            batch = CancelReason(r.code, r.message, r.initiator, self._seq, time.monotonic_ns())
            victims = list(self._queued.values()) + list(self.in_flight.values())
            self._queued.clear()
            self._queues.clear()
            self.in_flight.clear()
            self._active_by_fn.clear()
            for st in victims:
                self._bury(st, Outcome.CANCELLED, batch, None)
            self.cancelled_calls += len(victims)
            if victims:
                self._event("calls_cancelled_batch", "warn", None, count=len(victims),
                            reason_code=batch.code.value)
            return len(victims)

    def trap_all(self) -> int:
        with self:
            self._fault("trap")
            victims = list(self._queued.values()) + list(self.in_flight.values())
            self._queued.clear()
            self._queues.clear()
            self.in_flight.clear()
            self._active_by_fn.clear()
            for st in victims:
                self._bury(st, Outcome.TRAPPED, None, None)
            self.trapped_calls += len(victims)
            if victims:
                self._event("callee_trapped", "error", None, count=len(victims))
            return len(victims)

    # -- listeners / generations ---------------------------------------------

    def add_terminal_listener(self, call_id: int, listener: TerminalListener) -> Tombstone | None:
        """Register a one-shot terminal callback.  If the call is already terminal the
        tombstone is returned and the listener is *not* registered (no lost wakeup)."""
        with self:
            if call_id in self.in_flight or call_id in self._queued:
                if call_id in self._listeners:
                    raise ValueError(f"call {call_id} already has a terminal listener")
                self._listeners[call_id] = listener
                return None
            tomb = self._terminal.get(call_id)
            if tomb is None:
                self._classify_missing(call_id, "listen")
            return tomb

    def remove_terminal_listener(self, call_id: int) -> None:
        with self._lock:
            self._listeners.pop(call_id, None)

    def renew_generation(self) -> int:
        """Start a new epoch after a drain.  Old-generation ids are rejected thereafter."""
        with self:
            if self.in_flight or self._queued:
                raise RuntimeError("renew_generation requires a drained instance")
            self.generation += 1
            self._ids = CallIdAllocator(self.call_id_bits, self._ids.warn_at / self._ids.max_id)
            self._terminal.clear()
            self._listeners.clear()
            self._exhaustion_warned = False
            self._event("generation_renewed", "warn", None)
            return self.generation


_SHARED_TOMBS: dict = {}

COUNTERS = (
    "reentrancy_refusals", "concurrency_refusals", "queue_refusals", "queued_calls", "bridge_calls",
    "double_delivery_attempts", "completed_calls", "cancelled_calls", "trapped_calls",
    "tombstone_evictions", "expired_late_events", "stale_generation_events", "sink_failures",
    "listener_failures", "trace_context_rejected",
)
