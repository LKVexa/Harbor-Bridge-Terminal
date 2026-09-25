"""Security-focused reference model for INV-35 high-performance VM I/O.

This module intentionally has no dependency on ``pk_core`` so that the datapath
validation model can be tested in isolation.  It is not a production virtio or
vhost implementation; it models the safety invariants that an implementation
must preserve at a guest/host ring boundary.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import RLock

#: Maximum descriptors permitted in a single submitted chain.
MAX_CHAIN = 16

#: Maximum descriptor entries permitted in flight on one queue.
QUEUE_DEPTH = 64


class DescriptorInvalid(PermissionError):
    """Raised when guest-controlled descriptor state is not safe to consume."""


class QueueFull(RuntimeError):
    """Raised when accepting a chain would exceed the queue's descriptor bound."""


@dataclass(frozen=True, slots=True)
class MemoryRegion:
    """A registered, contiguous guest-memory interval ``[base, base + length)``."""

    base: int
    length: int

    def __post_init__(self) -> None:
        if not _is_int(self.base) or not _is_int(self.length):
            raise TypeError("memory-region base and length must be integers")
        if self.base < 0:
            raise ValueError("memory-region base must be non-negative")
        if self.length <= 0:
            raise ValueError("memory-region length must be positive")

    @property
    def limit(self) -> int:
        return self.base + self.length

    def contains(self, address: int, size: int) -> bool:
        """Return whether this single region covers the full descriptor range."""
        if not _is_int(address) or not _is_int(size) or address < 0 or size < 0:
            return False
        if size == 0:
            return self.base <= address <= self.limit
        return address >= self.base and address + size <= self.limit


@dataclass(frozen=True, slots=True)
class Descriptor:
    """A guest-controlled descriptor snapshot.

    Fields deliberately are not validated in ``__post_init__``: malformed values
    model hostile ring contents and must be rejected at the trust boundary in
    :meth:`VirtQueue.submit`.
    """

    index: object
    address: object
    length: object
    next_index: object | None = None


@dataclass
class VirtQueue:
    """Bounded virtqueue reference model with fail-closed descriptor validation."""

    name: str
    regions: tuple[MemoryRegion, ...]
    #: Optional tighter bounds (v4.3.0, INV-35-C028/C067). They may only lower the
    #: compiled-in MAX_CHAIN/QUEUE_DEPTH ceilings, never raise them.
    depth_limit: int = QUEUE_DEPTH
    chain_limit: int = MAX_CHAIN
    byte_limit: int | None = None
    in_flight: int = field(default=0, init=False)  # submitted chains/buffers
    pending: int = field(default=0, init=False)
    notifications_suppressed: int = field(default=0, init=False)
    completed: list[dict[str, object]] = field(default_factory=list, init=False)
    in_flight_descriptors: int = field(default=0, init=False)
    _submitted_sizes: deque[int] = field(default_factory=deque, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("queue name must be a non-empty string")
        if not isinstance(self.regions, tuple):
            self.regions = tuple(self.regions)
        if not all(isinstance(region, MemoryRegion) for region in self.regions):
            raise TypeError("regions must contain MemoryRegion values")
        self.regions = tuple(sorted(self.regions, key=lambda region: region.base))
        if not _is_int(self.depth_limit) or not 1 <= self.depth_limit <= QUEUE_DEPTH:
            raise ValueError(f"depth_limit must be an integer in [1, {QUEUE_DEPTH}]")
        if not _is_int(self.chain_limit) or not 1 <= self.chain_limit <= MAX_CHAIN:
            raise ValueError(f"chain_limit must be an integer in [1, {MAX_CHAIN}]")
        if self.byte_limit is not None and (not _is_int(self.byte_limit) or self.byte_limit <= 0):
            raise ValueError("byte_limit must be a positive integer or None")

    def _in_guest_memory(self, address: int, size: int) -> bool:
        """Validate a range against the union of registered guest regions.

        Adjacent/overlapping registered regions are treated as one covered range,
        while any gap causes a fail-closed rejection.
        """
        if not _is_int(address) or not _is_int(size) or address < 0 or size < 0:
            return False
        if size == 0:
            return any(region.base <= address <= region.limit for region in self.regions)

        end = address + size
        cursor = address
        for region in self.regions:
            if region.limit <= cursor:
                continue
            if region.base > cursor:
                return False
            cursor = max(cursor, region.limit)
            if cursor >= end:
                return True
        return False

    def submit(self, chain: Mapping[object, object], head: object) -> dict[str, object]:
        """Snapshot and validate a descriptor chain before mutating queue state.

        All guest-controlled fields are checked before they affect queue counters.
        Queue capacity is enforced in descriptor entries, preventing multiple
        maximum-length chains from bypassing the intended queue-depth limit.
        """
        if not isinstance(chain, Mapping):
            raise DescriptorInvalid(f"{self.name}: descriptor chain must be a mapping")
        if not _valid_index(head):
            raise DescriptorInvalid(f"{self.name}: invalid head descriptor index {head!r}")

        # Freeze the ring view used for this validation pass. Descriptor is frozen,
        # so a caller cannot mutate a descriptor after the mapping snapshot.
        try:
            snapshot = dict(chain)
        except Exception as exc:
            raise DescriptorInvalid(f"{self.name}: descriptor mapping could not be snapshotted") from exc
        for slot in snapshot:
            if not _valid_index(slot):
                raise DescriptorInvalid(f"{self.name}: invalid descriptor slot index {slot!r}")

        seen: set[int] = set()
        index: int | None = int(head)
        total_bytes = 0
        walked: list[int] = []

        while index is not None:
            if index in seen:
                raise DescriptorInvalid(f"{self.name}: descriptor chain loops at {index}")
            if len(walked) >= self.chain_limit:
                raise DescriptorInvalid(f"{self.name}: chain exceeds {self.chain_limit} descriptors")
            seen.add(index)

            desc = snapshot.get(index)
            if not isinstance(desc, Descriptor):
                if desc is None:
                    raise DescriptorInvalid(f"{self.name}: descriptor {index} is not in the ring")
                raise DescriptorInvalid(f"{self.name}: slot {index} is not a Descriptor")
            if not _valid_index(desc.index) or desc.index != index:
                raise DescriptorInvalid(
                    f"{self.name}: slot {index} holds a descriptor claiming index {desc.index!r}"
                )
            if not _is_int(desc.address) or not _is_int(desc.length):
                raise DescriptorInvalid(f"{self.name}: descriptor {index} has non-integer fields")
            if desc.address < 0:
                raise DescriptorInvalid(f"{self.name}: descriptor {index} has a negative address")
            if desc.length < 0:
                raise DescriptorInvalid(f"{self.name}: descriptor {index} has a negative length")
            if not self._in_guest_memory(desc.address, desc.length):
                raise DescriptorInvalid(
                    f"{self.name}: descriptor {index} at {hex(desc.address)}+{desc.length} "
                    "is outside registered guest memory"
                )
            if desc.next_index is not None and not _valid_index(desc.next_index):
                raise DescriptorInvalid(
                    f"{self.name}: descriptor {index} has invalid next index {desc.next_index!r}"
                )

            walked.append(index)
            total_bytes += desc.length
            index = None if desc.next_index is None else int(desc.next_index)

        descriptor_count = len(walked)
        if descriptor_count == 0:  # defensive; a valid head always walks at least one
            raise DescriptorInvalid(f"{self.name}: empty descriptor chain")

        if self.byte_limit is not None and total_bytes > self.byte_limit:
            raise DescriptorInvalid(
                f"{self.name}: chain of {total_bytes} bytes exceeds byte limit {self.byte_limit}"
            )

        with self._lock:
            if self.in_flight_descriptors + descriptor_count > self.depth_limit:
                raise QueueFull(
                    f"{self.name}: accepting {descriptor_count} descriptors would exceed "
                    f"queue depth {self.depth_limit} (currently {self.in_flight_descriptors})"
                )
            self.in_flight += 1
            self.pending += 1
            self.in_flight_descriptors += descriptor_count
            self._submitted_sizes.append(descriptor_count)

        return {
            "schema": "PK_VIRTQUEUE_SUBMIT/1",
            "queue": self.name,
            "descriptors": walked,
            "descriptor_count": descriptor_count,
            "bytes": total_bytes,
            "validated": True,
        }

    def complete(self, *, guest_wants_notification: bool) -> dict[str, object]:
        """Complete one submitted chain while preserving wakeup liveness."""
        if not isinstance(guest_wants_notification, bool):
            raise TypeError("guest_wants_notification must be bool")

        with self._lock:
            if self.in_flight == 0 or not self._submitted_sizes:
                raise RuntimeError(f"{self.name}: nothing in flight to complete")

            released = self._submitted_sizes.popleft()
            self.in_flight -= 1
            self.pending -= 1
            self.in_flight_descriptors -= released

            # In this reference policy, suppression is permitted only when the
            # guest requested it and the queue is drained. Pending work forces a
            # wakeup, preventing suppression from stranding live work.
            suppress = not guest_wants_notification and self.pending == 0
            if suppress:
                self.notifications_suppressed += 1
            record = {"notified": not suppress, "descriptors_released": released}
            self.completed.append(record)
            if len(self.completed) > QUEUE_DEPTH:
                del self.completed[:-QUEUE_DEPTH]

            return {
                "schema": "PK_VIRTQUEUE_COMPLETE/1",
                "queue": self.name,
                "notified": not suppress,
                "pending": self.pending,
                "in_flight_descriptors": self.in_flight_descriptors,
                "descriptors_released": released,
            }


def _is_int(value: object) -> bool:
    """True only for integers, excluding ``bool`` (an ``int`` subclass)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_index(value: object) -> bool:
    return _is_int(value) and value >= 0
