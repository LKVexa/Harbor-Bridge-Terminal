"""Dependency-independent reference model for the INV-38 kernel-bypass data path.

This module deliberately does not import ``pk_core``.  It provides the small,
deterministic model used by the component's behavioural checks and by local
unit tests when the wider Post-Kubernetes core is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Final

DEFAULT_ADDRESS_BITS: Final = 64
DEFAULT_MAX_REGIONS: Final = 1024
DEFAULT_COMPLETION_LIMIT: Final = 4096


class BypassError(Exception):
    """Base class for deterministic kernel-bypass model failures."""

    code = "PK_BYPASS_ERROR"


class OutOfBounds(BypassError, ValueError):
    """Raised when a memory region or descriptor is outside its legal range."""

    code = "PK_BYPASS_OUT_OF_BOUNDS"


class NotRegistered(BypassError, KeyError):
    """Raised for a region key that is unknown or was deregistered."""

    code = "PK_BYPASS_NOT_REGISTERED"


class RegionBusy(BypassError, RuntimeError):
    """Raised when deregistration is attempted while descriptors are in flight."""

    code = "PK_BYPASS_REGION_BUSY"


class RingFull(BypassError, RuntimeError):
    """Raised when the submission ring has no free slots."""

    code = "PK_BYPASS_RING_FULL"


class CompletionRingFull(BypassError, RuntimeError):
    """Raised when completions cannot be published without exceeding the bound."""

    code = "PK_BYPASS_COMPLETION_RING_FULL"


class RegionLimitReached(BypassError, RuntimeError):
    """Raised when the configured registered-region ceiling has been reached."""

    code = "PK_BYPASS_REGION_LIMIT"


def _require_plain_int(value: int, *, name: str, minimum: int | None = None) -> int:
    """Validate integer API inputs without accepting bool as an integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class _Descriptor:
    key: int
    addr: int
    length: int
    payload: bytes


@dataclass
class BypassQueue:
    """A bounded, thread-safe model of a registration-backed bypass queue.

    The model intentionally snapshots the payload on ``post``.  A real DMA path
    would pin/register memory and rely on ownership rules, but a Python model
    that retained a mutable ``bytearray``/``memoryview`` would otherwise permit
    caller-side mutation after validation (a TOCTOU analogue).
    """

    ring_size: int = 8
    available: bool = True
    address_bits: int = DEFAULT_ADDRESS_BITS
    max_regions: int = DEFAULT_MAX_REGIONS
    completion_limit: int = DEFAULT_COMPLETION_LIMIT
    regions: dict[int, tuple[int, int]] = field(default_factory=dict, init=False)
    ring: list[_Descriptor] = field(default_factory=list, init=False)
    completions: list[tuple[str, bytes]] = field(default_factory=list, init=False)
    _next_key: int = field(default=1, init=False, repr=False)
    violations: int = field(default=0, init=False)
    fallbacks: int = field(default=0, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_plain_int(self.ring_size, name="ring_size", minimum=1)
        if not isinstance(self.available, bool):
            raise TypeError("available must be a bool")
        _require_plain_int(self.address_bits, name="address_bits", minimum=1)
        _require_plain_int(self.max_regions, name="max_regions", minimum=1)
        _require_plain_int(self.completion_limit, name="completion_limit", minimum=1)
        if self.address_bits > 128:
            raise ValueError("address_bits must be <= 128")

    @property
    def max_address(self) -> int:
        return (1 << self.address_bits) - 1

    @property
    def region_count(self) -> int:
        with self._lock:
            return len(self.regions)

    @property
    def ring_depth(self) -> int:
        with self._lock:
            return len(self.ring)

    @property
    def completion_depth(self) -> int:
        with self._lock:
            return len(self.completions)

    def _validate_range(self, addr: int, length: int, *, context: str) -> tuple[int, int]:
        _require_plain_int(addr, name=f"{context} address")
        _require_plain_int(length, name=f"{context} length")
        if addr < 0 or length <= 0:
            self.violations += 1
            raise OutOfBounds(f"{context} address must be >= 0 and length must be > 0")
        if addr > self.max_address or length - 1 > self.max_address - addr:
            self.violations += 1
            raise OutOfBounds(
                f"{context} {addr:#x}+{length} exceeds {self.address_bits}-bit address space"
            )
        return addr, length

    def _ensure_completion_capacity(self, additional: int) -> None:
        if len(self.completions) + additional > self.completion_limit:
            raise CompletionRingFull(
                f"completion limit {self.completion_limit} would be exceeded"
            )

    def set_available(self, available: bool) -> None:
        """Atomically enable/disable bypass selection for subsequent posts."""
        if not isinstance(available, bool):
            raise TypeError("available must be a bool")
        with self._lock:
            self.available = available

    def register(self, base: int, length: int) -> int:
        with self._lock:
            self._validate_range(base, length, context="region")
            if len(self.regions) >= self.max_regions:
                raise RegionLimitReached(f"maximum {self.max_regions} registered regions reached")
            key = self._next_key
            self._next_key += 1
            self.regions[key] = (base, length)
            return key

    def deregister(self, key: int) -> None:
        _require_plain_int(key, name="key", minimum=1)
        with self._lock:
            if key not in self.regions:
                raise NotRegistered(key)
            if any(descriptor.key == key for descriptor in self.ring):
                raise RegionBusy(f"region {key} still has in-flight descriptors")
            del self.regions[key]

    def post(self, key: int, addr: int, length: int, payload: bytes | bytearray | memoryview) -> str:
        _require_plain_int(key, name="key", minimum=0)
        with self._lock:
            self._validate_range(addr, length, context="descriptor")
            if not isinstance(payload, (bytes, bytearray, memoryview)):
                raise TypeError("payload must be bytes-like")
            payload_bytes = bytes(payload)
            if len(payload_bytes) > length:
                self.violations += 1
                raise OutOfBounds(
                    f"payload length {len(payload_bytes)} exceeds descriptor length {length}"
                )

            if not self.available:
                # Kernel fallback does not require a device MR key, but it still uses
                # the validated descriptor shape and a bounded completion queue.
                self._ensure_completion_capacity(len(self.ring) + 1)
                self._poll_locked()
                self.completions.append(("kernel", payload_bytes))
                self.fallbacks += 1
                return "kernel"

            if key not in self.regions:
                raise NotRegistered(key)
            base, size = self.regions[key]
            region_end = base + size
            descriptor_end = addr + length
            if addr < base or descriptor_end > region_end:
                self.violations += 1
                raise OutOfBounds(f"{addr:#x}+{length} outside region {key}")
            if len(self.ring) >= self.ring_size:
                raise RingFull(f"{self.ring_size} slots in use")
            self.ring.append(_Descriptor(key, addr, length, payload_bytes))
            return "bypass"

    def _poll_locked(self, max_items: int | None = None) -> int:
        if max_items is None:
            count = len(self.ring)
        else:
            _require_plain_int(max_items, name="max_items", minimum=0)
            count = min(max_items, len(self.ring))
        self._ensure_completion_capacity(count)
        completed = self.ring[:count]
        self.completions.extend(("bypass", descriptor.payload) for descriptor in completed)
        del self.ring[:count]
        return count

    def poll(self, max_items: int | None = None) -> int:
        with self._lock:
            return self._poll_locked(max_items)

    def pop_completion(self) -> tuple[str, bytes] | None:
        """Consume the oldest completion, or return ``None`` when none are ready."""
        with self._lock:
            if not self.completions:
                return None
            return self.completions.pop(0)
