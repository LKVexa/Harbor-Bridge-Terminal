"""Runtime reference model for INV-15's host-owned asynchronous ABI.

This module intentionally has no dependency on ``pk_core`` so the ABI state
machine can be imported, tested, fuzzed, and embedded independently from the
checklist/certification framework.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
import secrets
from threading import RLock
from types import MappingProxyType
from typing import Any, Iterable, Mapping

DEFAULT_BUDGET = 8
DEFAULT_TOMBSTONE_LIMIT = 64
MAX_SEQUENCE = (1 << 63) - 1
_NO_IMMEDIATE = object()


class AsyncAbiError(RuntimeError):
    """Base class for runtime ABI failures."""


class BudgetExhausted(AsyncAbiError):
    """Raised when an instance already holds its maximum live subtasks."""


class ForeignHandle(AsyncAbiError):
    """Raised for malformed, forged, unknown, or differently scoped handles."""


class HandleConsumed(AsyncAbiError):
    """Raised when a retired subtask handle is used again."""


class SubtaskNotReady(AsyncAbiError):
    """Raised when a caller tries to consume a pending subtask."""


class WaitSetTooLarge(AsyncAbiError):
    """Raised when a wait request exceeds the instance's bounded live set."""


class HandleSpaceExhausted(AsyncAbiError):
    """Raised if the bounded sequence namespace is exhausted."""


class SubtaskState(str, Enum):
    """Legal states of a live subtask in the host-owned table."""

    PENDING = "pending"
    READY = "ready"


@dataclass(frozen=True, slots=True)
class SubtaskHandle:
    """Opaque, unguessable reference to one host-owned subtask.

    Every handle receives a fresh 128-bit random token. Sequence numbers remain
    diagnostic only; knowing one valid handle does not reveal enough authority
    to synthesize another handle in the same or a different instance.
    """

    token: str = field(repr=False)
    sequence: int


@dataclass(frozen=True, slots=True)
class Subtask:
    """One live asynchronous call owned by the host."""

    handle: SubtaskHandle
    state: SubtaskState = SubtaskState.PENDING
    value: Any = None

    @property
    def ready(self) -> bool:
        return self.state is SubtaskState.READY


@dataclass
class AsyncAbi:
    """Thread-safe, host-owned waitable table for one component instance.

    Important invariants:

    * live-table size never exceeds ``budget``;
    * every live handle carries independent unguessable authority;
    * pending values cannot be consumed;
    * retirement removes payloads from the live table immediately;
    * a bounded tombstone set preserves useful use-after-consume diagnostics
      without allowing historical handles to grow memory without bound;
    * no operation parks a guest stack.
    """

    instance: str
    budget: int = DEFAULT_BUDGET
    tombstone_limit: int = DEFAULT_TOMBSTONE_LIMIT
    _table: dict[SubtaskHandle, Subtask] = field(default_factory=dict, init=False, repr=False)
    blocked_stacks: int = field(default=0, init=False)
    refusals: int = field(default=0, init=False)
    cancellations: int = field(default=0, init=False)
    abandoned_ready: int = field(default=0, init=False)
    cancellation_reasons: dict[str, int] = field(default_factory=dict, init=False)
    _next: int = field(default=1, init=False, repr=False)
    _retired: set[SubtaskHandle] = field(default_factory=set, init=False, repr=False)
    _retired_order: deque[SubtaskHandle] = field(default_factory=deque, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.instance, str) or not self.instance.strip():
            raise ValueError("instance must be a non-empty string")
        if isinstance(self.budget, bool) or not isinstance(self.budget, int) or self.budget < 1:
            raise ValueError(f"budget must be a positive integer, got {self.budget!r}")
        if (
            isinstance(self.tombstone_limit, bool)
            or not isinstance(self.tombstone_limit, int)
            or self.tombstone_limit < 1
        ):
            raise ValueError(
                f"tombstone_limit must be a positive integer, got {self.tombstone_limit!r}"
            )

    @property
    def table(self) -> Mapping[SubtaskHandle, Subtask]:
        """Read-only snapshot of the host-owned live table for diagnostics."""
        with self._lock:
            return MappingProxyType(dict(self._table))

    @property
    def open_subtasks(self) -> int:
        with self._lock:
            return len(self._table)

    def call(self, immediate: Any = _NO_IMMEDIATE):
        """Start a call and return ``("value", v)`` or ``("subtask", handle)``.

        ``None`` is a valid synchronous value; omitting ``immediate`` is what
        selects asynchronous execution.
        """
        if immediate is not _NO_IMMEDIATE:
            return ("value", immediate)

        with self._lock:
            if len(self._table) >= self.budget:
                self.refusals += 1
                raise BudgetExhausted(
                    f"{self.instance}: {len(self._table)} outstanding subtasks, budget {self.budget}"
                )
            if self._next > MAX_SEQUENCE:
                raise HandleSpaceExhausted(f"{self.instance}: subtask handle space exhausted")

            handle = SubtaskHandle(secrets.token_hex(16), self._next)
            self._next += 1
            self._table[handle] = Subtask(handle=handle)
            return ("subtask", handle)

    def _validate_handle(self, handle: object) -> SubtaskHandle:
        if not isinstance(handle, SubtaskHandle):
            raise ForeignHandle(f"{self.instance}: invalid subtask handle type")
        if not isinstance(handle.token, str) or len(handle.token) != 32:
            raise ForeignHandle(f"{self.instance}: malformed subtask handle token")
        return handle

    def _task(self, handle: object) -> Subtask:
        valid = self._validate_handle(handle)
        if valid in self._retired:
            raise HandleConsumed(f"handle {valid.sequence} already consumed")
        task = self._table.get(valid)
        if task is None:
            raise ForeignHandle(f"{self.instance}: unknown or forged handle {valid.sequence}")
        return task

    def _retire(self, handle: SubtaskHandle) -> None:
        self._table.pop(handle, None)
        self._retired.add(handle)
        self._retired_order.append(handle)
        while len(self._retired_order) > self.tombstone_limit:
            expired = self._retired_order.popleft()
            self._retired.discard(expired)

    @staticmethod
    def _reason_key(reason: object) -> str:
        if not isinstance(reason, str):
            raise ValueError("cancellation reason must be a string")
        text = reason.strip() or "unspecified"
        return text[:128]

    def _count_reason(self, reason: object) -> None:
        key = self._reason_key(reason)
        if key in self.cancellation_reasons or len(self.cancellation_reasons) < 32:
            self.cancellation_reasons[key] = self.cancellation_reasons.get(key, 0) + 1
        else:
            self.cancellation_reasons["__other__"] = self.cancellation_reasons.get("__other__", 0) + 1

    def complete(self, handle: SubtaskHandle, value: Any) -> None:
        """Publish a result exactly once for a live pending subtask."""
        with self._lock:
            task = self._task(handle)
            if task.ready:
                raise HandleConsumed(f"handle {handle.sequence} already completed")
            self._table[handle] = Subtask(
                handle=handle, state=SubtaskState.READY, value=value
            )

    def wait(self, handles: Iterable[SubtaskHandle]) -> list[SubtaskHandle]:
        """Return ready members of a bounded waitable set without blocking.

        The iterable is consumed exactly once, so generators and other one-shot
        iterators behave correctly. Duplicate handles are collapsed because the
        ABI primitive is a set, not a multiset. User iterator code is never run
        while the host-table lock is held.
        """
        try:
            iterator = iter(handles)
        except TypeError as exc:
            raise ForeignHandle(f"{self.instance}: wait set is not iterable") from exc

        requested: list[SubtaskHandle] = []
        for handle in iterator:
            if len(requested) >= self.budget:
                raise WaitSetTooLarge(
                    f"{self.instance}: wait set exceeds live-subtask budget {self.budget}"
                )
            requested.append(handle)

        with self._lock:
            ready: list[SubtaskHandle] = []
            seen: set[SubtaskHandle] = set()
            for handle in requested:
                task = self._task(handle)
                if handle in seen:
                    continue
                seen.add(handle)
                if task.ready:
                    ready.append(handle)
            return ready

    def take(self, handle: SubtaskHandle):
        """Consume and retire a ready subtask result exactly once."""
        with self._lock:
            task = self._task(handle)
            if not task.ready:
                raise SubtaskNotReady(f"handle {handle.sequence} is not ready")
            value = task.value
            self._retire(handle)
            return value

    def cancel(self, handle: SubtaskHandle, reason: str = "caller cancelled") -> bool:
        """Cancel or abandon one live handle and release its table row.

        Returns ``True`` when cancellation was propagated to pending work and
        ``False`` when the work had already completed and only its unread result
        was abandoned.
        """
        reason_key = self._reason_key(reason)
        with self._lock:
            task = self._task(handle)
            propagated = not task.ready
            if propagated:
                self.cancellations += 1
                self._count_reason(reason_key)
            else:
                self.abandoned_ready += 1
            self._retire(handle)
            return propagated

    def cancel_all(self, reason: str = "caller gone") -> int:
        """Release every live subtask when its caller disappears.

        Pending work is counted as propagated cancellation. Already-ready but
        unread results are abandoned and retired so caller loss cannot leak rows.
        """
        reason_key = self._reason_key(reason)
        with self._lock:
            pending = 0
            for handle in list(self._table):
                task = self._table[handle]
                if task.ready:
                    self.abandoned_ready += 1
                else:
                    pending += 1
                    self.cancellations += 1
                    self._count_reason(reason_key)
                self._retire(handle)
            return pending

    def snapshot(self) -> dict[str, object]:
        """Return bounded, payload-free diagnostics suitable for telemetry."""
        with self._lock:
            ready = sum(1 for task in self._table.values() if task.ready)
            return {
                "instance": self.instance,
                "subtasks_open": len(self._table),
                "subtasks_ready": ready,
                "budget": self.budget,
                "budget_refusals": self.refusals,
                "cancellations": self.cancellations,
                "abandoned_ready": self.abandoned_ready,
                "blocked_stacks": self.blocked_stacks,
                "retired_tombstones": len(self._retired),
            }
