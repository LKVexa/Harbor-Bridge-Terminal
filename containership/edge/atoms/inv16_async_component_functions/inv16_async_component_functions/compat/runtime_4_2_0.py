"""Thread-safe runtime model for INV-16 async component functions."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from types import MappingProxyType
from typing import Mapping


class ReentrancyRefused(RuntimeError):
    """Raised when re-entering an instance would corrupt an in-flight call."""


class ConcurrencyLimitReached(RuntimeError):
    """Raised when the configured per-instance in-flight budget is exhausted."""


class DoubleDelivery(RuntimeError):
    """Raised if a terminal call receives a second completion value."""


class CallCancelled(RuntimeError):
    """Raised if a value is delivered after the call has been cancelled."""


class CallTrapped(RuntimeError):
    """Raised if a value is delivered after the callee trapped."""


@dataclass(slots=True)
class CallState:
    """State for one in-flight call. Never shared with another call."""

    call_id: int
    function: str
    caller_is_async: bool = True
    value: object = None


@dataclass
class AsyncFunctions:
    """Guest-visible async function surface for one instance.

    The declaration table is frozen on construction, all lifecycle transitions are
    serialized, and terminal call ids are retained as compact tombstones so a late
    delivery cannot be mistaken for a never-issued call.
    """

    instance: str
    declared: Mapping[str, bool] = field(default_factory=dict)
    stateful: frozenset[str] = frozenset()
    concurrency_limit: int | None = None
    in_flight: dict[int, CallState] = field(default_factory=dict, init=False)
    _terminal: dict[int, str] = field(default_factory=dict, init=False, repr=False)
    _next: int = field(default=1, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    reentrancy_refusals: int = 0
    concurrency_refusals: int = 0
    bridge_calls: int = 0
    double_delivery_attempts: int = 0
    cancelled_calls: int = 0
    trapped_calls: int = 0

    def __post_init__(self) -> None:
        normalized: dict[str, bool] = {}
        for name, is_async in dict(self.declared).items():
            if not isinstance(name, str) or not name:
                raise ValueError("function names must be non-empty strings")
            if not isinstance(is_async, bool):
                raise TypeError(f"async declaration for {name!r} must be bool")
            normalized[name] = is_async
        unknown_stateful = set(self.stateful) - set(normalized)
        if unknown_stateful:
            raise ValueError(f"stateful functions must be declared: {sorted(unknown_stateful)!r}")
        if self.concurrency_limit is not None:
            if isinstance(self.concurrency_limit, bool) or not isinstance(self.concurrency_limit, int):
                raise TypeError("concurrency_limit must be an integer or None")
            if self.concurrency_limit < 1:
                raise ValueError("concurrency_limit must be >= 1")
        self.declared = MappingProxyType(normalized)
        self.stateful = frozenset(self.stateful)

    def is_async(self, function: str) -> bool:
        try:
            return self.declared[function]
        except KeyError as exc:
            raise ValueError(f"{function!r} is not declared on {self.instance}") from exc

    @property
    def calls_in_flight(self) -> int:
        with self._lock:
            return len(self.in_flight)

    def invoke(self, function: str, caller_is_async: bool = True) -> CallState:
        if not isinstance(caller_is_async, bool):
            raise TypeError("caller_is_async must be bool")
        async_decl = self.is_async(function)
        with self._lock:
            if self.concurrency_limit is not None and len(self.in_flight) >= self.concurrency_limit:
                self.concurrency_refusals += 1
                raise ConcurrencyLimitReached(
                    f"{self.instance} already has {len(self.in_flight)} calls in flight "
                    f"(limit {self.concurrency_limit})")
            if function in self.stateful and any(
                    state.function == function for state in self.in_flight.values()):
                self.reentrancy_refusals += 1
                raise ReentrancyRefused(
                    f"{function} holds state across suspension and is already in flight")
            if async_decl and not caller_is_async:
                self.bridge_calls += 1
            state = CallState(
                call_id=self._next, function=function, caller_is_async=caller_is_async)
            self._next += 1
            self.in_flight[state.call_id] = state
            return state

    def _take_live(self, call_id: int) -> CallState:
        if isinstance(call_id, bool) or not isinstance(call_id, int):
            raise ValueError(f"call {call_id!r} was never issued by {self.instance}")
        state = self.in_flight.pop(call_id, None)
        if state is not None:
            return state
        terminal = self._terminal.get(call_id)
        if terminal == "completed":
            self.double_delivery_attempts += 1
            raise DoubleDelivery(f"call {call_id} already delivered")
        if terminal == "cancelled":
            raise CallCancelled(f"call {call_id} was cancelled")
        if terminal == "trapped":
            raise CallTrapped(f"call {call_id} ended when the callee trapped")
        raise ValueError(f"call {call_id!r} was never issued by {self.instance}")

    def complete(self, call_id: int, value: object):
        with self._lock:
            state = self._take_live(call_id)
            state.value = value
            self._terminal[call_id] = "completed"
            return value

    def cancel(self, call_id: int, reason: str = "cancelled") -> CallState:
        with self._lock:
            state = self._take_live(call_id)
            self._terminal[call_id] = "cancelled"
            self.cancelled_calls += 1
            return state

    def cancel_all(self, reason: str = "caller gone") -> int:
        del reason  # reason is intentionally accepted for API/audit context, not retained as call state.
        with self._lock:
            call_ids = tuple(self.in_flight)
            for call_id in call_ids:
                self.in_flight.pop(call_id)
                self._terminal[call_id] = "cancelled"
            self.cancelled_calls += len(call_ids)
            return len(call_ids)

    def trap_all(self) -> int:
        with self._lock:
            call_ids = tuple(self.in_flight)
            for call_id in call_ids:
                self.in_flight.pop(call_id)
                self._terminal[call_id] = "trapped"
            self.trapped_calls += len(call_ids)
            return len(call_ids)

