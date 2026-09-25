"""Hardened in-memory reference broker implementations for INV-54.

These classes are deliberately dependency-free so their core semantics can be
unit-tested without the external ``pk_core`` conformance framework.  They are
reference implementations, not production replacements for Kafka, RabbitMQ, or
AWS SQS.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any
import zlib


def _require_string(value: object, *, field_name: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_int(value: object, *, field_name: str, minimum: int | None = None) -> int:
    # bool is an int subclass in Python; accepting True as partition 1 or offset 1
    # is surprising and can hide configuration/input mistakes, so reject it.
    if type(value) is not int:  # noqa: E721 - intentional exact-type validation
        raise TypeError(f"{field_name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return value


@dataclass
class FanoutBroker:
    """Thread-safe, in-memory fan-out reference broker.

    Each publish creates an independent deep copy for every subscriber.  Copies
    are prepared before any inbox is mutated, so a copy failure cannot produce a
    partial fan-out delivery.
    """

    subscribers: dict[str, list[Any]] = field(default_factory=dict, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def subscribe(self, name: str) -> list[Any]:
        name = _require_string(name, field_name="subscriber name")
        with self._lock:
            return self.subscribers.setdefault(name, [])

    def unsubscribe(self, name: str) -> bool:
        name = _require_string(name, field_name="subscriber name")
        with self._lock:
            return self.subscribers.pop(name, None) is not None

    def publish(self, msg: Any) -> int:
        with self._lock:
            inboxes = list(self.subscribers.values())
            try:
                deliveries = [deepcopy(msg) for _ in inboxes]
            except Exception as exc:  # deepcopy can raise arbitrary user-code exceptions
                raise TypeError("message must be deep-copyable for isolated fan-out delivery") from exc
            for inbox, delivery in zip(inboxes, deliveries):
                inbox.append(delivery)
            return len(inboxes)


@dataclass(frozen=True)
class PartitionedLog:
    """Thread-safe, in-memory partitioned log with independent consumer offsets."""

    partitions: int = 4
    logs: list[list[tuple[str, Any]]] = field(default_factory=list, init=False)
    offsets: dict[tuple[str, int], int] = field(default_factory=dict, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_int(self.partitions, field_name="partitions", minimum=1)
        object.__setattr__(self, "logs", [[] for _ in range(self.partitions)])

    def partition_for(self, key: str) -> int:
        key = _require_string(key, field_name="key", allow_empty=True)
        return zlib.crc32(key.encode("utf-8")) % self.partitions

    def append(self, key: str, msg: Any) -> tuple[int, int]:
        key = _require_string(key, field_name="key", allow_empty=True)
        partition = self.partition_for(key)
        with self._lock:
            self.logs[partition].append((key, msg))
            return partition, len(self.logs[partition]) - 1

    def _check_partition(self, partition: int) -> int:
        partition = _require_int(partition, field_name="partition", minimum=0)
        if partition >= self.partitions:
            raise IndexError(f"partition {partition} out of range")
        return partition

    def poll(self, consumer: str, partition: int, limit: int = 100) -> list[tuple[str, Any]]:
        consumer = _require_string(consumer, field_name="consumer")
        partition = self._check_partition(partition)
        limit = _require_int(limit, field_name="limit", minimum=0)
        with self._lock:
            offset = self.offsets.get((consumer, partition), 0)
            batch = self.logs[partition][offset : offset + limit]
            self.offsets[(consumer, partition)] = offset + len(batch)
            return list(batch)

    def seek(self, consumer: str, partition: int, offset: int) -> None:
        consumer = _require_string(consumer, field_name="consumer")
        partition = self._check_partition(partition)
        offset = _require_int(offset, field_name="offset", minimum=0)
        with self._lock:
            if offset > len(self.logs[partition]):
                raise IndexError(f"offset {offset} out of range")
            self.offsets[(consumer, partition)] = offset

    def committed_offset(self, consumer: str, partition: int) -> int:
        consumer = _require_string(consumer, field_name="consumer")
        partition = self._check_partition(partition)
        with self._lock:
            return self.offsets.get((consumer, partition), 0)

    def end_offset(self, partition: int) -> int:
        partition = self._check_partition(partition)
        with self._lock:
            return len(self.logs[partition])
