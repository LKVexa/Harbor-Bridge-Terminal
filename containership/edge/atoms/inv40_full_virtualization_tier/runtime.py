"""Standalone runtime model for INV-40 full virtualization.

This module deliberately has no dependency on ``pk_core`` so the security- and
lifecycle-critical behavior can be unit tested even when the orchestration
framework is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4

BOOT_BUDGET_MS = 8_000
FOOTPRINT_CEILING_MIB = 2_048

FULL_DEVICE_MODEL = frozenset(
    {
        "virtio-net",
        "virtio-block",
        "virtio-balloon",
        "virtio-rng",
        "virtio-console",
        "ahci",
        "usb-xhci",
        "vga",
        "rtc",
        "acpi",
        "smbios",
        "tpm",
    }
)


class FullVmError(RuntimeError):
    """Base class for machine-readable operational VM failures."""

    code = "PK_FULL_VM_ERROR"

    def as_dict(self) -> dict[str, str]:
        return {"schema": "PK_FULL_VM_ERROR/1", "code": self.code, "message": str(self)}


class PrimitiveRequired(FullVmError):
    """Raised when the host cannot provide hardware virtualization."""

    code = "PK_FULL_VM_PRIMITIVE_REQUIRED"


class FootprintExceeded(FullVmError):
    """Raised when a guest's measured resident footprint exceeds the ceiling."""

    code = "PK_FULL_VM_FOOTPRINT_EXCEEDED"


class InvalidVmState(FullVmError):
    """Raised when an operation is illegal for the current VM lifecycle state."""

    code = "PK_FULL_VM_INVALID_STATE"


class DeviceConflict(FullVmError):
    """Raised when a device instance is already leased by another live guest."""

    code = "PK_FULL_VM_DEVICE_CONFLICT"


def _require_nonempty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > 255:
        raise ValueError(f"{field_name} must be at most 255 characters")
    return value


def _require_int(value: object, field_name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if positive and value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    if not positive and value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return value


class DeviceLeaseRegistry:
    """Thread-safe ownership registry for concrete device instances.

    Device *types* (``virtio-net``, ``tpm``, etc.) are not ownership tokens.
    Each VM therefore carries a mapping from device type to an instance ID.
    The registry rejects an attempt to lease any already-owned instance to a
    different live VM, including another VM in the same tenant.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._claims: dict[str, tuple[str, str, str]] = {}

    def claim(self, vm: "FullVm") -> None:
        with self._lock:
            conflicts: list[str] = []
            for instance_id in vm.device_instance_ids:
                owner = self._claims.get(instance_id)
                if owner is not None and owner[0] != vm.instance_id:
                    conflicts.append(instance_id)
            if conflicts:
                raise DeviceConflict(
                    f"{vm.name}: {len(conflicts)} device instance(s) already leased"
                )
            for instance_id in vm.device_instance_ids:
                self._claims[instance_id] = (vm.instance_id, vm.tenant, vm.name)

    def release(self, vm: "FullVm") -> None:
        with self._lock:
            for instance_id in vm.device_instance_ids:
                owner = self._claims.get(instance_id)
                if owner is not None and owner[0] == vm.instance_id:
                    del self._claims[instance_id]

    def owner_of(self, instance_id: str) -> tuple[str, str, str] | None:
        with self._lock:
            return self._claims.get(instance_id)

    def active_claim_count(self) -> int:
        with self._lock:
            return len(self._claims)


DEFAULT_DEVICE_LEASES = DeviceLeaseRegistry()


@dataclass
class FullVm:
    """A complete VM with an opaque guest OS and explicit device ownership."""

    name: str
    tenant: str
    memory_mib: int
    devices: frozenset[str] = FULL_DEVICE_MODEL
    device_instances: Mapping[str, str] | None = None
    instance_id: str = field(default_factory=lambda: uuid4().hex)
    state: str = field(init=False, default="created")
    boot_ms: int | None = field(init=False, default=None)
    resident_mib: int = field(init=False, default=0)
    _registry: DeviceLeaseRegistry | None = field(init=False, default=None, repr=False)
    _lock: RLock = field(init=False, default_factory=RLock, repr=False)

    def __post_init__(self) -> None:
        self.name = _require_nonempty_text(self.name, "name")
        self.tenant = _require_nonempty_text(self.tenant, "tenant")
        self.memory_mib = _require_int(self.memory_mib, "memory_mib", positive=True)
        self.instance_id = _require_nonempty_text(self.instance_id, "instance_id")

        try:
            normalized_devices = frozenset(self.devices)
        except TypeError as exc:
            raise TypeError("devices must be an iterable of strings") from exc
        if not normalized_devices or not all(isinstance(item, str) and item for item in normalized_devices):
            raise ValueError("devices must contain non-empty string device types")
        missing = FULL_DEVICE_MODEL - normalized_devices
        if missing:
            raise ValueError(
                "full virtualization requires the complete baseline device model; "
                f"missing: {', '.join(sorted(missing))}"
            )
        self.devices = normalized_devices

        if self.device_instances is None:
            token = self.instance_id
            mapping = {kind: f"{token}:{kind}" for kind in sorted(self.devices)}
        else:
            mapping = dict(self.device_instances)
            if set(mapping) != set(self.devices):
                raise ValueError("device_instances must define exactly one instance for every device type")
            if not all(isinstance(v, str) and v.strip() for v in mapping.values()):
                raise ValueError("device instance IDs must be non-empty strings")
            if len(set(mapping.values())) != len(mapping):
                raise ValueError("device instance IDs must be unique within a guest")
        self.device_instances = MappingProxyType(mapping)

    @property
    def device_instance_ids(self) -> frozenset[str]:
        return frozenset(self.device_instances.values())

    def start(
        self,
        *,
        primitive_usable: bool,
        elapsed_ms: int,
        resident_mib: int,
        registry: DeviceLeaseRegistry | None = None,
    ) -> dict[str, object]:
        """Start or restart the VM after validating the isolation boundary."""
        elapsed_ms = _require_int(elapsed_ms, "elapsed_ms")
        resident_mib = _require_int(resident_mib, "resident_mib")
        if not isinstance(primitive_usable, bool):
            raise TypeError("primitive_usable must be a boolean")

        with self._lock:
            if self.state == "destroyed":
                raise InvalidVmState(f"{self.name}: destroyed VM cannot be started")
            if self.state == "running":
                raise InvalidVmState(f"{self.name}: VM is already running")
            if not primitive_usable:
                raise PrimitiveRequired(
                    f"{self.name}: full virtualization requires the hardware primitive; "
                    "software emulation is not offered as an equivalent"
                )
            if resident_mib > FOOTPRINT_CEILING_MIB:
                raise FootprintExceeded(
                    f"{self.name}: {resident_mib}MiB resident exceeds the "
                    f"{FOOTPRINT_CEILING_MIB}MiB ceiling"
                )

            lease_registry = registry or DEFAULT_DEVICE_LEASES
            lease_registry.claim(self)
            self._registry = lease_registry
            self.boot_ms = elapsed_ms
            self.resident_mib = resident_mib
            self.state = "running"
            within_budget = elapsed_ms <= BOOT_BUDGET_MS
            return {
                "schema": "PK_FULL_VM_BOOT/1",
                "guest": self.name,
                "tenant": self.tenant,
                "state": self.state,
                "boot_ms": elapsed_ms,
                "budget_ms": BOOT_BUDGET_MS,
                "within_budget": within_budget,
                "status": "ok" if within_budget else "degraded",
                "resident_mib": resident_mib,
                "devices": len(self.devices),
                "device_instances": len(self.device_instance_ids),
                "guest_os_opaque": True,
                "cost_note": (
                    "seconds to boot and hundreds of MiB resident: choose this tier for "
                    "hostile or foreign guests, not by default"
                ),
            }

    def stop(self) -> dict[str, object]:
        """Stop a running VM and release all concrete device leases."""
        with self._lock:
            if self.state == "destroyed":
                raise InvalidVmState(f"{self.name}: destroyed VM cannot be stopped")
            if self.state != "running":
                raise InvalidVmState(f"{self.name}: only a running VM can be stopped")
            if self._registry is not None:
                self._registry.release(self)
            self._registry = None
            self.state = "stopped"
            self.resident_mib = 0
            return {"schema": "PK_FULL_VM_STATE/1", "guest": self.name, "state": self.state, "destroyed": False}

    def destroy(self) -> dict[str, object]:
        """Destroy the VM, releasing leases if needed; repeat destroys are idempotent."""
        with self._lock:
            if self.state == "destroyed":
                return {"schema": "PK_FULL_VM_STATE/1", "guest": self.name, "state": self.state, "destroyed": True, "idempotent": True}
            if self._registry is not None:
                self._registry.release(self)
            self._registry = None
            self.resident_mib = 0
            self.state = "destroyed"
            return {"schema": "PK_FULL_VM_STATE/1", "guest": self.name, "state": self.state, "destroyed": True, "idempotent": False}


def device_conflict(a: FullVm, b: FullVm) -> bool:
    """Return whether two distinct VMs reference any same concrete device instance."""
    return a.instance_id != b.instance_id and bool(a.device_instance_ids & b.device_instance_ids)
