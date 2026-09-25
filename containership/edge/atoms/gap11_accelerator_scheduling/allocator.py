"""Hardened accelerator allocation state machine for GAP-11.

This module deliberately has no dependency on ``pk_core`` so the security-
critical allocation rules can be unit-tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import secrets
import threading
from typing import Iterable


class AcceleratorSchedulingError(RuntimeError):
    """Base error carrying a stable machine-readable code and safe details."""

    code = "ACCELERATOR_SCHEDULING_ERROR"

    def __init__(self, message: str, **details: object) -> None:
        super().__init__(message)
        self.details = dict(details)

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class NoMatchingAccelerator(AcceleratorSchedulingError):
    """Raised when no available device satisfies the declared requirement."""

    code = "NO_MATCHING_ACCELERATOR"


class ScrubRequired(AcceleratorSchedulingError):
    """Raised when a device cannot safely serve the requested tenant."""

    code = "SCRUB_REQUIRED"


class UndeclaredPartition(AcceleratorSchedulingError, ValueError):
    """Raised when a requested partition is not declared by matching hardware."""

    code = "UNDECLARED_PARTITION"


class AmbiguousRelease(AcceleratorSchedulingError, ValueError):
    """Raised when device-only release would match more than one active lease."""

    code = "AMBIGUOUS_RELEASE"


class InvalidAcceleratorConfiguration(AcceleratorSchedulingError, ValueError):
    """Raised when inventory contains contradictory or unsafe declarations."""

    code = "INVALID_ACCELERATOR_CONFIGURATION"


def _clean_nonempty(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _clean_features(features: Iterable[str]) -> frozenset[str]:
    if isinstance(features, (str, bytes)):
        raise ValueError("features must be an iterable of feature names, not a string")
    try:
        cleaned = frozenset(features)
    except TypeError as exc:
        raise ValueError("features must be an iterable of strings") from exc
    if any(not isinstance(feature, str) or not feature.strip() for feature in cleaned):
        raise ValueError("features must contain only non-empty strings")
    return frozenset(feature.strip() for feature in cleaned)


@dataclass(frozen=True, slots=True)
class PartitionSpec:
    """Hardware-declared accelerator partition capability.

    ``memory_gb=None`` is intentionally treated as *unattested capacity*.  Such a
    partition may satisfy a request with ``memory_gb=0`` but cannot be used to
    claim a positive memory guarantee until inventory reports its capacity.
    """

    name: str
    memory_gb: int | None = None
    features: frozenset[str] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_nonempty(self.name, "partition name"))
        if self.memory_gb is not None:
            if isinstance(self.memory_gb, bool) or not isinstance(self.memory_gb, int) or self.memory_gb <= 0:
                raise InvalidAcceleratorConfiguration(
                    "partition memory_gb must be a positive integer or None",
                    partition=self.name,
                )
        if self.features is not None:
            object.__setattr__(self, "features", _clean_features(self.features))


@dataclass(frozen=True, slots=True)
class AllocationLease:
    """One exclusive allocation claim."""

    lease_id: str
    tenant: str
    workload: str
    partition: str | None

    def holder_tuple(self) -> tuple[str, str, str | None]:
        return (self.tenant, self.workload, self.partition)


@dataclass
class Accelerator:
    """One physical accelerator with optional hardware-declared partitions.

    A physical device has one security tenant between successful scrubs.  This
    allows several non-overlapping partitions to serve the *same* tenant while
    refusing cross-tenant co-residency and whole-device/partition overlap.
    """

    device: str
    generation: str
    memory_gb: int
    features: frozenset[str] = frozenset()
    partitions: tuple[PartitionSpec | str, ...] = ()
    kind: str = "generic"
    leases: dict[str, AllocationLease] = field(default_factory=dict, init=False, repr=False)
    security_tenant: str | None = field(default=None, init=False)
    scrubbed: bool = field(default=True, init=False)
    quarantined: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.device = _clean_nonempty(self.device, "device")
        self.generation = _clean_nonempty(self.generation, "generation")
        self.kind = _clean_nonempty(self.kind, "kind").lower()
        if isinstance(self.memory_gb, bool) or not isinstance(self.memory_gb, int) or self.memory_gb <= 0:
            raise InvalidAcceleratorConfiguration(
                "accelerator memory_gb must be a positive integer", device=self.device
            )
        self.features = _clean_features(self.features)

        normalized: list[PartitionSpec] = []
        for item in self.partitions:
            if isinstance(item, PartitionSpec):
                spec = item
            elif isinstance(item, str):
                spec = PartitionSpec(item)
            else:
                raise InvalidAcceleratorConfiguration(
                    "partitions must contain only PartitionSpec or string names",
                    device=self.device,
                )
            if spec.memory_gb is not None and spec.memory_gb > self.memory_gb:
                raise InvalidAcceleratorConfiguration(
                    "partition memory exceeds physical device memory",
                    device=self.device,
                    partition=spec.name,
                )
            if spec.features is not None and not spec.features <= self.features:
                raise InvalidAcceleratorConfiguration(
                    "partition declares features absent from physical device",
                    device=self.device,
                    partition=spec.name,
                )
            normalized.append(spec)
        names = [spec.name for spec in normalized]
        if len(names) != len(set(names)):
            raise InvalidAcceleratorConfiguration(
                "duplicate partition names on accelerator", device=self.device
            )
        known_partition_memory = sum(spec.memory_gb or 0 for spec in normalized)
        if known_partition_memory > self.memory_gb:
            raise InvalidAcceleratorConfiguration(
                "declared simultaneous partition memory exceeds physical device memory",
                device=self.device,
                declared_partition_memory_gb=known_partition_memory,
                physical_memory_gb=self.memory_gb,
            )
        self.partitions = tuple(normalized)

    @property
    def free(self) -> bool:
        """True only when the entire physical accelerator has no active lease."""
        return not self.leases

    @property
    def holder(self) -> tuple[str, str, str | None] | None:
        """Backward-compatible single-holder view.

        Returns ``None`` when free and the sole holder tuple when exactly one
        lease exists.  Multiple partition leases intentionally have no single
        holder and return ``None``; callers needing full state should use
        ``AcceleratorPool.allocations()``.
        """
        if len(self.leases) != 1:
            return None
        return next(iter(self.leases.values())).holder_tuple()

    @property
    def last_tenant(self) -> str | None:
        """Compatibility alias for the physical security tenant."""
        return self.security_tenant

    def partition_spec(self, name: str) -> PartitionSpec | None:
        return next((spec for spec in self.partitions if spec.name == name), None)

    def matches_physical(
        self, *, kind: str | None, generation: str | None, memory_gb: int, features: frozenset[str]
    ) -> bool:
        if kind is not None and self.kind != kind:
            return False
        if generation is not None and self.generation != generation:
            return False
        return self.memory_gb >= memory_gb and features <= self.features

    def partition_matches(self, name: str, *, memory_gb: int, features: frozenset[str]) -> bool:
        spec = self.partition_spec(name)
        if spec is None:
            return False
        if memory_gb > 0 and (spec.memory_gb is None or spec.memory_gb < memory_gb):
            return False
        effective_features = self.features if spec.features is None else spec.features
        return features <= effective_features

    def partition_available(self, name: str) -> bool:
        if any(lease.partition is None for lease in self.leases.values()):
            return False
        return all(lease.partition != name for lease in self.leases.values())

    def scrub(self, *, succeeds: bool = True) -> dict[str, object]:
        """Scrub device memory. Any active lease makes scrubbing illegal."""
        if self.leases:
            raise ScrubRequired(
                f"{self.device} has active leases; release before scrubbing",
                device=self.device,
                lease_count=len(self.leases),
            )
        self.scrubbed = bool(succeeds)
        self.quarantined = not self.scrubbed
        if self.scrubbed:
            self.security_tenant = None
        return {
            "schema": "PK_SCRUB/1",
            "device": self.device,
            "completed": self.scrubbed,
            "quarantined": self.quarantined,
        }


@dataclass
class AcceleratorPool:
    """Thread-safe exclusive accelerator allocator with tenant scrub barriers."""

    devices: list[Accelerator] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        names = [device.device for device in self.devices]
        if len(names) != len(set(names)):
            raise InvalidAcceleratorConfiguration("duplicate accelerator device identifiers")

    @staticmethod
    def _validate_request(
        *, tenant: str, workload: str, memory_gb: int, kind: str | None, generation: str | None,
        features: Iterable[str], partition: str | None,
    ) -> tuple[str, str, int, str | None, str | None, frozenset[str], str | None]:
        tenant = _clean_nonempty(tenant, "tenant")
        workload = _clean_nonempty(workload, "workload")
        if isinstance(memory_gb, bool) or not isinstance(memory_gb, int) or memory_gb < 0:
            raise ValueError(f"{workload}: memory_gb must be a non-negative integer")
        if kind is not None:
            kind = _clean_nonempty(kind, "kind").lower()
        if generation is not None:
            generation = _clean_nonempty(generation, "generation")
        feature_set = _clean_features(features)
        if partition is not None:
            partition = _clean_nonempty(partition, "partition")
        return tenant, workload, memory_gb, kind, generation, feature_set, partition

    def _new_lease_id(self) -> str:
        # 128 bits of randomness; collision checked under the pool lock.
        while True:
            candidate = secrets.token_hex(16)
            if all(candidate not in device.leases for device in self.devices):
                return candidate

    def allocate(
        self, *, tenant: str, workload: str, memory_gb: int = 0, kind: str | None = None,
        generation: str | None = None, features: Iterable[str] = frozenset(),
        partition: str | None = None,
    ) -> dict[str, object]:
        tenant, workload, memory_gb, kind, generation, feature_set, partition = self._validate_request(
            tenant=tenant,
            workload=workload,
            memory_gb=memory_gb,
            kind=kind,
            generation=generation,
            features=features,
            partition=partition,
        )

        with self._lock:
            # First establish hardware capability, independent of occupancy, so an
            # undeclared partition is never misreported as a generic capacity miss.
            physical = [
                device for device in self.devices
                if device.matches_physical(
                    kind=kind,
                    generation=generation,
                    memory_gb=0 if partition is not None else memory_gb,
                    features=frozenset() if partition is not None else feature_set,
                )
            ]
            if partition is not None:
                declaring = [device for device in physical if device.partition_spec(partition) is not None]
                if not declaring:
                    raise UndeclaredPartition(
                        f"no matching device declares partition {partition!r}", partition=partition
                    )
                capable = [
                    device for device in declaring
                    if device.partition_matches(partition, memory_gb=memory_gb, features=feature_set)
                ]
            else:
                capable = physical

            if not capable:
                raise NoMatchingAccelerator(
                    f"{workload}: no device satisfies kind={kind} generation={generation} memory>={memory_gb}GB "
                    f"features={sorted(feature_set)} partition={partition!r}",
                    workload=workload,
                    kind=kind,
                    generation=generation,
                    memory_gb=memory_gb,
                    partition=partition,
                )

            available = [
                device for device in capable
                if (device.partition_available(partition) if partition is not None else device.free)
            ]
            if not available:
                raise NoMatchingAccelerator(
                    f"{workload}: matching accelerator capacity is currently allocated",
                    workload=workload,
                    partition=partition,
                )

            safe = [
                device for device in available
                if not device.quarantined
                and (device.security_tenant is None or device.security_tenant == tenant)
            ]
            if not safe:
                device = min(available, key=lambda d: (d.memory_gb, d.device))
                if device.quarantined:
                    raise ScrubRequired(
                        f"{device.device} is quarantined after a failed scrub",
                        device=device.device,
                        tenant=tenant,
                        quarantined=True,
                    )
                raise ScrubRequired(
                    f"{device.device} belongs to tenant security epoch {device.security_tenant}; "
                    f"scrub required before {tenant}",
                    device=device.device,
                    previous_tenant=device.security_tenant,
                    requested_tenant=tenant,
                )

            # Best-fit on attested capacity. For partitions, use partition capacity
            # when known and physical capacity as a stable tiebreaker otherwise.
            def fit_key(device: Accelerator) -> tuple[int, int, str]:
                if partition is None:
                    return (device.memory_gb, device.memory_gb, device.device)
                spec = device.partition_spec(partition)
                partition_memory = spec.memory_gb if spec and spec.memory_gb is not None else 2**31 - 1
                return (partition_memory, device.memory_gb, device.device)

            device = min(safe, key=fit_key)
            lease = AllocationLease(
                lease_id=self._new_lease_id(),
                tenant=tenant,
                workload=workload,
                partition=partition,
            )
            device.leases[lease.lease_id] = lease
            device.security_tenant = tenant
            # Once a tenant starts using the device it is no longer in a clean,
            # cross-tenant handoff state, even before release.
            device.scrubbed = False

            return {
                "schema": "PK_ACCELERATOR_ALLOCATION/1",
                "lease_id": lease.lease_id,
                "device": device.device,
                "tenant": tenant,
                "workload": workload,
                "partition": partition,
                "kind": device.kind,
                "generation": device.generation,
                "memory_gb": (
                    device.memory_gb
                    if partition is None
                    else device.partition_spec(partition).memory_gb
                ),
            }

    def release(
        self, device_name: str, *, lease_id: str | None = None,
        workload: str | None = None, partition: str | None = None,
    ) -> dict[str, object]:
        """Release exactly one lease.

        Device-only release remains backward-compatible when the device has one
        active lease. With multiple partition leases it fails closed rather than
        releasing an arbitrary tenant workload.
        """
        device_name = _clean_nonempty(device_name, "device_name")
        with self._lock:
            device = next((d for d in self.devices if d.device == device_name), None)
            if device is None:
                raise KeyError(f"{device_name}: no such device")
            leases = list(device.leases.values())
            if lease_id is not None:
                leases = [lease for lease in leases if lease.lease_id == lease_id]
            if workload is not None:
                workload = _clean_nonempty(workload, "workload")
                leases = [lease for lease in leases if lease.workload == workload]
            if partition is not None:
                partition = _clean_nonempty(partition, "partition")
                leases = [lease for lease in leases if lease.partition == partition]
            if not leases:
                raise KeyError(f"{device_name}: no matching active lease")
            if len(leases) != 1:
                raise AmbiguousRelease(
                    f"{device_name}: release matches {len(leases)} leases; specify lease_id",
                    device=device_name,
                    matches=len(leases),
                )
            lease = leases[0]
            del device.leases[lease.lease_id]
            # security_tenant intentionally remains until a successful scrub.
            device.scrubbed = False
            return {
                "schema": "PK_ACCELERATOR_RELEASE/1",
                "lease_id": lease.lease_id,
                "device": device.device,
                "tenant": lease.tenant,
                "workload": lease.workload,
                "partition": lease.partition,
                "released": True,
                "scrub_required_for_tenant_change": True,
            }

    def release_lease(self, lease_id: str) -> dict[str, object]:
        lease_id = _clean_nonempty(lease_id, "lease_id")
        with self._lock:
            for device in self.devices:
                if lease_id in device.leases:
                    return self.release(device.device, lease_id=lease_id)
        raise KeyError(f"{lease_id}: no such active lease")

    def scrub(self, device_name: str, *, succeeds: bool = True) -> dict[str, object]:
        device_name = _clean_nonempty(device_name, "device_name")
        with self._lock:
            device = next((d for d in self.devices if d.device == device_name), None)
            if device is None:
                raise KeyError(f"{device_name}: no such device")
            return device.scrub(succeeds=succeeds)

    def allocations(self) -> dict[str, dict[str, object]]:
        """Return an immutable snapshot keyed by lease ID."""
        with self._lock:
            return {
                lease.lease_id: {
                    "device": device.device,
                    "tenant": lease.tenant,
                    "workload": lease.workload,
                    "partition": lease.partition,
                }
                for device in self.devices
                for lease in device.leases.values()
            }

    def inventory(self, *, include_sensitive: bool = False) -> dict[str, object]:
        """Return the typed inventory/control-plane snapshot.

        Tenant identity is omitted by default so a general inventory consumer
        does not receive cross-tenant metadata accidentally.
        """
        with self._lock:
            devices: list[dict[str, object]] = []
            for device in self.devices:
                record: dict[str, object] = {
                    "device": device.device,
                    "kind": device.kind,
                    "generation": device.generation,
                    "memory_gb": device.memory_gb,
                    "features": sorted(device.features),
                    "partitions": [
                        {
                            "name": spec.name,
                            "memory_gb": spec.memory_gb,
                            "features": (
                                sorted(device.features)
                                if spec.features is None
                                else sorted(spec.features)
                            ),
                        }
                        for spec in device.partitions
                    ],
                    "active_leases": len(device.leases),
                    "scrubbed": device.scrubbed,
                    "quarantined": device.quarantined,
                }
                if include_sensitive:
                    record["security_tenant"] = device.security_tenant
                devices.append(record)
            return {"schema": "PK_ACCELERATOR_INVENTORY/1", "devices": devices}
