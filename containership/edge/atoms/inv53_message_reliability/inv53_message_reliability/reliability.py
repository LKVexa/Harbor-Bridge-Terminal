"""Framework-independent message reliability primitives for INV-53.

The implementation is intentionally in-memory and reference-grade: persistence,
distributed fencing and broker replication belong to downstream broker adapters.
The primitives nevertheless enforce the safety properties that can be proven in a
single process: opaque lease tokens, bounded delivery attempts, dead-lettering,
copy isolation, duplicate-active-id rejection, and thread-safe state transitions.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from numbers import Real
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4

Message = dict[str, Any]


class ReliabilityError(RuntimeError):
    """Base exception for reliability primitive failures."""


class DuplicateMessageError(ReliabilityError):
    """Raised when the same logical message id is active more than once."""


class QueueCapacityError(ReliabilityError):
    """Raised before accepting work that would exceed a configured hard limit."""


class DeduplicationCapacityError(ReliabilityError):
    """Raised before an effect when the bounded deduplication set is full."""


@dataclass(frozen=True, slots=True)
class Delivery:
    """A leased delivery.

    ``lease_id`` is a fencing token.  Acknowledgements for an older lease are
    rejected after the message has been redelivered under a new lease.
    """

    message: Message
    lease_id: str
    deadline: float
    attempt: int

    @property
    def message_id(self) -> str:
        return self.message["id"]

    def __getitem__(self, key: str) -> Any:
        """Compatibility convenience for older ``delivery[\"id\"]`` callers."""
        return self.message[key]


@dataclass(frozen=True, slots=True)
class DeadLetter:
    """Terminal record for a message that is no longer eligible for delivery."""

    message: Message
    attempts: int
    reason: str
    last_lease_id: str | None


@dataclass(slots=True)
class _LeaseRecord:
    message: Message
    lease_id: str
    deadline: float
    attempt: int


class ReliableQueue:
    """Thread-safe, in-memory reference queue with at-least-once semantics.

    This class is not a durable broker.  It is a semantic reference used by the
    INV-53 component and its tests.  Downstream broker implementations must make
    equivalent state transitions durable and distributed.
    """

    def __init__(
        self,
        *,
        visibility: Real = 10,
        max_attempts: int = 3,
        max_ready: int | None = None,
        max_in_flight: int | None = None,
        max_dead_letters: int | None = None,
    ) -> None:
        self.visibility = self._positive_number(visibility, "visibility")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be an integer >= 1")
        self.max_attempts = max_attempts
        self.max_ready = self._optional_positive_int(max_ready, "max_ready")
        self.max_in_flight = self._optional_positive_int(max_in_flight, "max_in_flight")
        self.max_dead_letters = self._optional_positive_int(max_dead_letters, "max_dead_letters")

        self._ready: deque[Message] = deque()
        self._in_flight: dict[str, _LeaseRecord] = {}
        self._attempts: dict[str, int] = {}
        self._active_ids: set[str] = set()
        self._dlq: deque[DeadLetter] = deque()
        self._redeliveries = 0
        self._acks = 0
        self._ack_rejections = 0
        self._nacks = 0
        self._lock = RLock()

    @staticmethod
    def _positive_number(value: Real, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{name} must be a real number")
        number = float(value)
        if not isfinite(number) or number <= 0:
            raise ValueError(f"{name} must be finite and > 0")
        return number

    @staticmethod
    def _optional_positive_int(value: int | None, name: str) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be None or an integer >= 1")
        return value

    @staticmethod
    def _time(value: Real) -> float:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError("now must be a real number")
        number = float(value)
        if not isfinite(number):
            raise ValueError("now must be finite")
        return number

    @staticmethod
    def _message_id(message: Mapping[str, Any]) -> str:
        raw = message.get("id")
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("message must carry a non-empty string id")
        msg_id = raw.strip()
        if len(msg_id) > 512:
            raise ValueError("message id must be <= 512 characters")
        return msg_id

    @staticmethod
    def _copy_message(message: Mapping[str, Any]) -> Message:
        if not isinstance(message, Mapping):
            raise TypeError("message must be a mapping")
        copied = deepcopy(dict(message))
        copied["id"] = ReliableQueue._message_id(copied)
        return copied

    @staticmethod
    def _within_limit(current: int, limit: int | None, name: str) -> None:
        if limit is not None and current >= limit:
            raise QueueCapacityError(f"{name} capacity reached ({limit})")

    @property
    def ready_count(self) -> int:
        with self._lock:
            return len(self._ready)

    @property
    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    @property
    def dead_letter_count(self) -> int:
        with self._lock:
            return len(self._dlq)

    @property
    def redeliveries(self) -> int:
        with self._lock:
            return self._redeliveries

    @property
    def dlq(self) -> tuple[DeadLetter, ...]:
        """Return a defensive snapshot of dead-letter records."""
        with self._lock:
            return tuple(
                DeadLetter(deepcopy(item.message), item.attempts, item.reason, item.last_lease_id)
                for item in self._dlq
            )

    def snapshot(self) -> dict[str, int]:
        """Return low-cardinality counters/gauges suitable for test telemetry."""
        with self._lock:
            return {
                "ready": len(self._ready),
                "in_flight": len(self._in_flight),
                "dead_lettered": len(self._dlq),
                "redeliveries": self._redeliveries,
                "acks": self._acks,
                "ack_rejections": self._ack_rejections,
                "nacks": self._nacks,
                "tracked_attempts": len(self._attempts),
            }

    def put(self, message: Mapping[str, Any]) -> None:
        """Accept a new logical message after validation and copy isolation."""
        copied = self._copy_message(message)
        msg_id = copied["id"]
        with self._lock:
            self._within_limit(len(self._ready), self.max_ready, "ready queue")
            if msg_id in self._active_ids:
                raise DuplicateMessageError(f"message id already active: {msg_id!r}")
            self._ready.append(copied)
            self._active_ids.add(msg_id)

    def receive(self, *, now: Real) -> Delivery | None:
        """Lease the next message after expiring older leases."""
        current = self._time(now)
        with self._lock:
            self._expire_locked(current)
            if not self._ready:
                return None
            self._within_limit(len(self._in_flight), self.max_in_flight, "in-flight")

            message = self._ready.popleft()
            msg_id = message["id"]
            attempt = self._attempts.get(msg_id, 0) + 1
            if attempt > self.max_attempts:
                # Normal transitions dead-letter before this point. Preserve the
                # message if internal state is ever inconsistent rather than lose it.
                self._ready.appendleft(message)
                raise ReliabilityError("attempt counter exceeded cap before leasing")

            lease_id = uuid4().hex
            deadline = current + self.visibility
            self._attempts[msg_id] = attempt
            self._in_flight[msg_id] = _LeaseRecord(message, lease_id, deadline, attempt)
            return Delivery(deepcopy(message), lease_id, deadline, attempt)

    @staticmethod
    def _lease_parts(delivery: Delivery | str, lease_id: str | None) -> tuple[str, str | None]:
        if isinstance(delivery, Delivery):
            return delivery.message_id, delivery.lease_id
        if not isinstance(delivery, str) or not delivery.strip():
            raise ValueError("delivery must be a Delivery or non-empty message id")
        return delivery.strip(), lease_id

    def ack(
        self,
        delivery: Delivery | str,
        lease_id: str | None = None,
        *,
        now: Real,
    ) -> bool:
        """Acknowledge only the currently active, unexpired lease.

        Supplying only a message id is intentionally insufficient; callers using
        a string id must also supply the matching opaque ``lease_id``.  ``now`` is
        required so a lease cannot be settled after its visibility deadline merely
        because no receive operation happened to process expiration first.
        """
        current = self._time(now)
        msg_id, token = self._lease_parts(delivery, lease_id)
        with self._lock:
            self._expire_locked(current)
            record = self._in_flight.get(msg_id)
            if record is None or token is None or token != record.lease_id:
                self._ack_rejections += 1
                return False
            del self._in_flight[msg_id]
            self._attempts.pop(msg_id, None)
            self._active_ids.discard(msg_id)
            self._acks += 1
            return True

    def nack(
        self,
        delivery: Delivery | str,
        *,
        now: Real,
        lease_id: str | None = None,
        requeue: bool = True,
        reason: str = "negative_acknowledgement",
    ) -> bool:
        """Reject the current lease and either requeue or dead-letter it."""
        current = self._time(now)
        msg_id, token = self._lease_parts(delivery, lease_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string")
        with self._lock:
            self._expire_locked(current)
            record = self._in_flight.get(msg_id)
            if record is None or token is None or token != record.lease_id:
                return False
            target_dlq = (not requeue) or record.attempt >= self.max_attempts
            if target_dlq:
                self._within_limit(len(self._dlq), self.max_dead_letters, "dead-letter queue")
            else:
                self._within_limit(len(self._ready), self.max_ready, "ready queue")
            del self._in_flight[msg_id]
            self._nacks += 1
            if target_dlq:
                self._dead_letter_locked(record.message, record.attempt, reason.strip(), record.lease_id)
            else:
                self._ready.append(record.message)
                self._redeliveries += 1
            return True

    def extend_visibility(
        self,
        delivery: Delivery | str,
        *,
        now: Real,
        extension: Real,
        lease_id: str | None = None,
    ) -> Delivery | None:
        """Extend the current lease from ``now`` and return its refreshed view."""
        current = self._time(now)
        extra = self._positive_number(extension, "extension")
        msg_id, token = self._lease_parts(delivery, lease_id)
        with self._lock:
            self._expire_locked(current)
            record = self._in_flight.get(msg_id)
            if record is None or token is None or token != record.lease_id:
                return None
            record.deadline = current + extra
            return Delivery(deepcopy(record.message), record.lease_id, record.deadline, record.attempt)

    def expire(self, *, now: Real) -> None:
        """Explicitly process visibility expirations without receiving new work."""
        current = self._time(now)
        with self._lock:
            self._expire_locked(current)

    def _expire_locked(self, now: float) -> None:
        expired = [
            (msg_id, record)
            for msg_id, record in self._in_flight.items()
            if now >= record.deadline
        ]
        # Stable iteration by id makes tests deterministic without promising order.
        for msg_id, record in sorted(expired, key=lambda item: item[0]):
            if self._in_flight.get(msg_id) is not record:
                continue
            target_dlq = record.attempt >= self.max_attempts
            if target_dlq:
                self._within_limit(len(self._dlq), self.max_dead_letters, "dead-letter queue")
            else:
                self._within_limit(len(self._ready), self.max_ready, "ready queue")
            del self._in_flight[msg_id]
            if target_dlq:
                self._dead_letter_locked(
                    record.message,
                    record.attempt,
                    "visibility_timeout",
                    record.lease_id,
                )
            else:
                self._ready.append(record.message)
                self._redeliveries += 1

    def _dead_letter_locked(
        self,
        message: Message,
        attempts: int,
        reason: str,
        last_lease_id: str | None,
    ) -> None:
        self._within_limit(len(self._dlq), self.max_dead_letters, "dead-letter queue")
        msg_id = message["id"]
        self._dlq.append(DeadLetter(deepcopy(message), attempts, reason, last_lease_id))
        self._attempts.pop(msg_id, None)
        self._active_ids.discard(msg_id)


class IdempotentConsumer:
    """Thread-safe in-memory deduplication reference.

    Production consumers should replace this memory set with a durable store that
    is transactionally coupled to the business effect.  ``max_entries`` provides a
    fail-closed bound so the reference implementation cannot grow without limit.
    """

    def __init__(self, *, max_entries: int = 100_000) -> None:
        if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be an integer >= 1")
        self.max_entries = max_entries
        self._done: set[tuple[str, str]] = set()
        self.effects = 0
        self.skipped = 0
        self._lock = RLock()

    @property
    def done_count(self) -> int:
        with self._lock:
            return len(self._done)

    def handle(self, message: Mapping[str, Any], *, scope: str = "default") -> bool:
        """Record one effect for a unique ``(scope, message_id)`` key.

        Returns ``True`` when the effect is admitted and ``False`` for a duplicate.
        The reference effect is represented by ``effects``; production code must
        atomically persist its dedupe key with the real side effect.
        """
        msg_id = ReliableQueue._message_id(message)
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("scope must be a non-empty string")
        key = (scope.strip(), msg_id)
        with self._lock:
            if key in self._done:
                self.skipped += 1
                return False
            if len(self._done) >= self.max_entries:
                raise DeduplicationCapacityError(
                    f"deduplication capacity reached ({self.max_entries}); refusing untracked effect"
                )
            self._done.add(key)
            self.effects += 1
            return True
