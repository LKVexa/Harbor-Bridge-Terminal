"""Framework-independent INV-24 microVM lifecycle domain model.

This module deliberately has no ``pk_core`` dependency so the safety-critical
configuration and lifecycle rules remain directly unit-testable in an isolated
checkout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Integral
from typing import Final

MINIMAL_DEVICE_MODEL: Final[frozenset[str]] = frozenset(
    {"virtio-net", "virtio-block", "virtio-vsock", "serial", "rtc"}
)
BOOT_BUDGET_MS: Final[int] = 125
MIN_VCPUS: Final[int] = 1
MAX_VCPUS: Final[int] = 32
MIN_MEMORY_MIB: Final[int] = 32
MAX_MEMORY_MIB: Final[int] = 131_072
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"stopped"})


class DeviceOutsideModel(PermissionError):
    """Raised when a requested device is not part of the minimal model."""


class BootBudgetExceeded(RuntimeError):
    """Raised when a cold boot takes longer than the declared budget."""


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{field_name} must not contain control characters")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must be non-empty")
    if len(value) > 128:
        raise ValueError(f"{field_name} must be at most 128 characters")
    return value


def _require_int(value: object, field_name: str, *, minimum: int, maximum: int) -> int:
    # bool is an Integral but accepting True as one vCPU is configuration ambiguity.
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer")
    value = int(value)
    if not minimum <= value <= maximum:
        raise ValueError(f"{field_name} must be in [{minimum}, {maximum}], got {value}")
    return value


@dataclass(slots=True)
class MicroVM:
    """One single-tenant microVM configuration and lifecycle state machine."""

    name: str
    tenant: str
    vcpus: int = 1
    memory_mib: int = 128
    devices: frozenset[str] = frozenset()
    state: str = "created"
    boot_ms: int | None = None
    destroyed: bool = False
    _sealed: bool = field(init=False, default=False, repr=False)

    def __setattr__(self, name: str, value: object) -> None:
        if name != "_sealed" and getattr(self, "_sealed", False):
            raise AttributeError(f"{self.__class__.__name__}.{name} is managed by the runtime")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        self.name = _require_text(self.name, "name")
        self.tenant = _require_text(self.tenant, "tenant")
        self.vcpus = _require_int(
            self.vcpus, "vcpus", minimum=MIN_VCPUS, maximum=MAX_VCPUS
        )
        self.memory_mib = _require_int(
            self.memory_mib,
            "memory_mib",
            minimum=MIN_MEMORY_MIB,
            maximum=MAX_MEMORY_MIB,
        )
        if self.state != "created" or self.boot_ms is not None or self.destroyed:
            raise ValueError("new MicroVM objects must start in the pristine created state")
        if isinstance(self.devices, str):
            raise TypeError("devices must be a collection of device names, not a string")
        try:
            devices = frozenset(self.devices)
        except TypeError as exc:
            raise TypeError("devices must be an iterable of hashable device names") from exc
        if any(not isinstance(device, str) for device in devices):
            raise TypeError("every device name must be a string")
        outside = devices - MINIMAL_DEVICE_MODEL
        if outside:
            raise DeviceOutsideModel(
                f"{self.name}: devices outside the minimal model: {sorted(outside)}"
            )
        self.devices = devices
        object.__setattr__(self, "_sealed", True)

    def create_record(self) -> dict[str, object]:
        """Return the stable public creation record without exposing mutable state."""
        return {
            "schema": "PK_MICROVM/1",
            "instance": self.name,
            "tenant": self.tenant,
            "vcpus": self.vcpus,
            "memory_mib": self.memory_mib,
            "devices": sorted(self.devices),
            "state": self.state,
        }

    def boot(self, *, elapsed_ms: int, budget_ms: int = BOOT_BUDGET_MS) -> dict[str, object]:
        if self.state != "created" or self.destroyed:
            raise RuntimeError(f"{self.name}: cannot boot from state {self.state!r}")
        elapsed_ms = _require_int(
            elapsed_ms, "elapsed_ms", minimum=0, maximum=2_147_483_647
        )
        budget_ms = _require_int(
            budget_ms, "budget_ms", minimum=1, maximum=BOOT_BUDGET_MS
        )
        object.__setattr__(self, "boot_ms", elapsed_ms)
        if elapsed_ms > budget_ms:
            object.__setattr__(self, "state", "failed")
            raise BootBudgetExceeded(
                f"{self.name}: cold boot took {elapsed_ms}ms against a {budget_ms}ms budget"
            )
        object.__setattr__(self, "state", "running")
        return {
            "schema": "PK_MICROVM_BOOT/1",
            "instance": self.name,
            "tenant": self.tenant,
            "boot_ms": elapsed_ms,
            "budget_ms": budget_ms,
            "devices": sorted(self.devices),
            "cold": True,
        }

    def pause(self) -> str:
        if self.state != "running" or self.destroyed:
            raise RuntimeError(f"{self.name}: cannot pause from {self.state!r}")
        object.__setattr__(self, "state", "paused")
        return self.state

    def resume(self) -> str:
        if self.state != "paused" or self.destroyed:
            raise RuntimeError(f"{self.name}: cannot resume from {self.state!r}")
        object.__setattr__(self, "state", "running")
        return self.state

    def stop(self) -> dict[str, object]:
        """Destroy instance state exactly once from any non-terminal state."""
        if self.destroyed or self.state in TERMINAL_STATES:
            raise RuntimeError(f"{self.name}: instance is already destroyed")
        if self.state not in {"created", "running", "paused", "failed"}:
            raise RuntimeError(f"{self.name}: cannot stop from state {self.state!r}")
        object.__setattr__(self, "state", "stopped")
        object.__setattr__(self, "destroyed", True)
        return {
            "schema": "PK_MICROVM_LIFECYCLE/1",
            "instance": self.name,
            "state": self.state,
            "destroyed": True,
        }

    def status(self) -> dict[str, object]:
        """Return a bounded operator-readable snapshot suitable for health surfaces."""
        return {
            "schema": "PK_MICROVM_STATUS/1",
            "instance": self.name,
            "tenant": self.tenant,
            "state": self.state,
            "destroyed": self.destroyed,
            "boot_ms": self.boot_ms,
            "vcpus": self.vcpus,
            "memory_mib": self.memory_mib,
            "devices": sorted(self.devices),
        }
