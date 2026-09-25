"""Security-sensitive snapshot domain model for INV-26.

This module intentionally has no dependency on ``pk_core`` so its tenant,
workload, environment, model, timing and entropy invariants can be unit-tested
in isolation.
"""
from __future__ import annotations

import hashlib
import json
import math
import secrets
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

RESTORE_BUDGET_MS = 10.0
ENTROPY_BYTES = 32
SNAPSHOT_SCHEMA = "PK_SNAPSHOT/2"
RESTORE_SCHEMA = "PK_SNAPSHOT_RESTORE/2"


class SnapshotError(Exception):
    """Base class for snapshot-domain failures."""


class SnapshotNotFound(SnapshotError, KeyError):
    """Raised when a restore names a snapshot the store does not hold."""


class SnapshotExists(SnapshotError, FileExistsError):
    """Raised when capture would overwrite an existing snapshot."""


class CrossTenantRestore(SnapshotError, PermissionError):
    """Raised when a snapshot is restored into another tenant."""


class WorkloadMismatch(SnapshotError, PermissionError):
    """Raised when a snapshot is restored for another workload."""


class EnvironmentMismatch(SnapshotError, PermissionError):
    """Raised when a snapshot crosses environment boundaries."""


class ModelMismatch(SnapshotError, ValueError):
    """Raised when the device model changed after capture."""


class EntropyInjectionFailed(SnapshotError, RuntimeError):
    """Raised when guest entropy cannot be injected during restore."""


def _require_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field_name} must not contain leading/trailing whitespace")
    return value


def normalize_devices(devices: Iterable[str]) -> tuple[str, ...]:
    """Return a deterministic device model after strict input validation."""
    if isinstance(devices, (str, bytes)):
        raise TypeError("devices must be an iterable of device identifiers, not a string/bytes")
    try:
        values = tuple(devices)
    except TypeError as exc:  # pragma: no cover - defensive clarity
        raise TypeError("devices must be iterable") from exc
    if not values:
        raise ValueError("devices must contain at least one device identifier")
    for value in values:
        _require_id(value, "device identifier")
    if len(set(values)) != len(values):
        raise ValueError("devices must not contain duplicate identifiers")
    return tuple(sorted(values))


def model_fingerprint(devices: Iterable[str]) -> str:
    """Return a full SHA-256 fingerprint of the canonical device model."""
    canonical = json.dumps(
        normalize_devices(devices), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Captured guest metadata, permanently bound to its security context."""

    name: str
    tenant: str
    workload: str
    environment: str
    fingerprint: str
    memory_mib: int
    entropy_stale: bool = True
    schema: str = SNAPSHOT_SCHEMA

    def canonical(self) -> bytes:
        """Canonical capture record suitable for signing or digesting."""
        value = {
            "schema": self.schema,
            "name": self.name,
            "tenant": self.tenant,
            "workload": self.workload,
            "environment": self.environment,
            "fingerprint": self.fingerprint,
            "memory_mib": self.memory_mib,
            "entropy_stale": self.entropy_stale,
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _default_entropy_injector(_snapshot: Snapshot, seed: bytes) -> None:
    """Reference-model injection hook.

    A production hypervisor adapter must replace this hook with an implementation
    that writes the supplied seed into the guest RNG interface. The reference
    model validates that fresh cryptographic material is generated and passed to
    an injector on every successful restore.
    """
    if len(seed) != ENTROPY_BYTES:
        raise EntropyInjectionFailed("invalid entropy seed length")


@dataclass
class SnapshotStore:
    """Thread-safe capture/restore model with mandatory security boundaries."""

    entropy_injector: Callable[[Snapshot, bytes], None] = _default_entropy_injector
    _snapshots: dict[str, Snapshot] = field(default_factory=dict, init=False, repr=False)
    _reseeds: int = field(default=0, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    @property
    def snapshots(self) -> Mapping[str, Snapshot]:
        with self._lock:
            return MappingProxyType(dict(self._snapshots))

    @property
    def reseeds(self) -> int:
        with self._lock:
            return self._reseeds

    def capture(
        self,
        *,
        name: str,
        tenant: str,
        workload: str,
        environment: str,
        devices: Iterable[str],
        memory_mib: int,
    ) -> Snapshot:
        name = _require_id(name, "snapshot name")
        tenant = _require_id(tenant, "tenant")
        workload = _require_id(workload, "workload")
        environment = _require_id(environment, "environment")
        if isinstance(memory_mib, bool) or not isinstance(memory_mib, int) or memory_mib <= 0:
            raise ValueError(f"memory_mib must be a positive int, got {memory_mib!r}")
        snap = Snapshot(
            name=name,
            tenant=tenant,
            workload=workload,
            environment=environment,
            fingerprint=model_fingerprint(devices),
            memory_mib=memory_mib,
        )
        with self._lock:
            if name in self._snapshots:
                raise SnapshotExists(f"{name}: a snapshot with this name already exists")
            self._snapshots[name] = snap
        return snap

    def restore(
        self,
        name: str,
        *,
        tenant: str,
        workload: str,
        environment: str,
        devices: Iterable[str],
        elapsed_ms: float | None = None,
    ) -> dict[str, object]:
        name = _require_id(name, "snapshot name")
        tenant = _require_id(tenant, "tenant")
        workload = _require_id(workload, "workload")
        environment = _require_id(environment, "environment")
        if elapsed_ms is not None:
            if isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, (int, float)):
                raise TypeError("elapsed_ms must be a finite non-negative number or None")
            if not math.isfinite(float(elapsed_ms)) or elapsed_ms < 0:
                raise ValueError("elapsed_ms must be finite and non-negative")

        with self._lock:
            try:
                snap = self._snapshots[name]
            except KeyError as exc:
                raise SnapshotNotFound(name) from exc

            if snap.tenant != tenant:
                raise CrossTenantRestore(
                    f"{name}: captured for tenant {snap.tenant!r}, cannot restore into {tenant!r}"
                )
            if snap.workload != workload:
                raise WorkloadMismatch(
                    f"{name}: captured for workload {snap.workload!r}, not {workload!r}"
                )
            if snap.environment != environment:
                raise EnvironmentMismatch(
                    f"{name}: captured in environment {snap.environment!r}, not {environment!r}"
                )
            fingerprint = model_fingerprint(devices)
            if fingerprint != snap.fingerprint:
                raise ModelMismatch(
                    f"{name}: device model changed since capture ({snap.fingerprint} -> {fingerprint})"
                )

            started = time.perf_counter_ns()
            seed = secrets.token_bytes(ENTROPY_BYTES)
            try:
                self.entropy_injector(snap, seed)
            except Exception as exc:
                raise EntropyInjectionFailed(f"{name}: guest entropy injection failed") from exc
            measured_ms = (time.perf_counter_ns() - started) / 1_000_000.0
            self._reseeds += 1

        duration_ms = float(elapsed_ms) if elapsed_ms is not None else measured_ms
        proof = hashlib.sha256(seed).hexdigest()
        return {
            "schema": RESTORE_SCHEMA,
            "snapshot": name,
            "tenant": tenant,
            "workload": workload,
            "environment": environment,
            "restore_ms": duration_ms,
            "budget_ms": RESTORE_BUDGET_MS,
            "within_budget": duration_ms <= RESTORE_BUDGET_MS,
            "entropy_reseeded": True,
            "entropy_proof_sha256": proof,
            "cold": False,
        }
