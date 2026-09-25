"""Pure resource model for INV-32 elastic virtualization.

This module intentionally has no dependency on ``pk_core`` so the safety-critical
resource state machine can be tested in isolation.  The surrounding component
adapter in :mod:`component` binds this model into the inventory/checklist system.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
import math
import threading
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

RESERVE_FRACTION = 0.10
RESOURCE_ADJUSTMENT_SCHEMA = "PK_RESOURCE_ADJUSTMENT/2"
LEGACY_RESOURCE_ADJUSTMENT_SCHEMA = "PK_RESOURCE_ADJUSTMENT/1"
HOST_RESOURCES_SCHEMA = "PK_HOST_RESOURCES/1"
AUDIT_EVENT_SCHEMA = "PK_RESOURCE_AUDIT/1"
ZERO_HASH = "0" * 64
MAX_IDENTIFIER_LENGTH = 255
MAX_OPERATION_ID_LENGTH = 128


class _StructuredErrorMixin:
    """Attach a stable machine-readable code and details to public failures."""

    code = "elastic_virtualization_error"

    def __init__(self, message: str, **details: Any) -> None:
        self.details = dict(details)
        super().__init__(message)  # type: ignore[call-arg]  # cooperative mixin

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class ReserveBreach(_StructuredErrorMixin, RuntimeError):
    code = "reserve_breach"


class FloorBreach(_StructuredErrorMixin, RuntimeError):
    code = "floor_breach"


class UnknownGuest(_StructuredErrorMixin, KeyError):
    code = "unknown_guest"


class InvalidAdjustmentRecord(_StructuredErrorMixin, ValueError):
    code = "invalid_adjustment_record"


class StaleAdjustment(_StructuredErrorMixin, RuntimeError):
    code = "stale_adjustment"


class ReplayConflict(_StructuredErrorMixin, RuntimeError):
    code = "replay_conflict"


class StateIntegrityError(_StructuredErrorMixin, RuntimeError):
    code = "state_integrity_error"


class AuditIntegrityError(_StructuredErrorMixin, RuntimeError):
    code = "audit_integrity_error"


def _require_int(name: str, value: Any, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _require_identifier(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must be non-empty")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{name} exceeds {MAX_IDENTIFIER_LENGTH} characters")
    return value


def _canonical_hash(event_without_hash: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(event_without_hash), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class Guest:
    """Immutable guest allocation state.

    Immutability prevents a caller from retaining the object passed to ``add`` and
    mutating memory or vCPU accounting behind the host's reserve checks.
    """

    name: str
    tenant: str
    memory_mib: int
    floor_mib: int
    ceiling_mib: int
    vcpus: int = 1
    vcpu_max: int = 4
    cooperative: bool = True

    def __post_init__(self) -> None:
        _require_identifier("guest name", self.name)
        _require_identifier("tenant", self.tenant)
        _require_int("memory_mib", self.memory_mib, minimum=0)
        _require_int("floor_mib", self.floor_mib, minimum=0)
        _require_int("ceiling_mib", self.ceiling_mib, minimum=0)
        _require_int("vcpus", self.vcpus, minimum=1)
        _require_int("vcpu_max", self.vcpu_max, minimum=1)
        if not isinstance(self.cooperative, bool):
            raise TypeError("cooperative must be a bool")
        if not self.floor_mib <= self.memory_mib <= self.ceiling_mib:
            raise ValueError(f"{self.name}: memory outside its own floor/ceiling")
        if self.vcpus > self.vcpu_max:
            raise ValueError(f"{self.name}: {self.vcpus} vCPUs outside [1, {self.vcpu_max}]")


@dataclass
class ElasticHost:
    """Thread-safe live memory and vCPU adjustment inside a hard host reserve.

    ``guests`` and ``history`` remain public for compatibility with the earlier
    reference model, but every mutating operation validates the current state and
    history before trusting them.  Guest objects themselves are immutable.
    """

    name: str
    total_mib: int
    reserve_fraction: float = RESERVE_FRACTION
    guests: dict[str, Guest] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    _free_page_reports: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _require_identifier("host name", self.name)
        _require_int("total_mib", self.total_mib, minimum=1)
        if isinstance(self.reserve_fraction, bool) or not isinstance(self.reserve_fraction, (int, float)):
            raise TypeError("reserve_fraction must be a number")
        if not math.isfinite(float(self.reserve_fraction)) or not 0 < float(self.reserve_fraction) < 1:
            raise ValueError("reserve_fraction must be finite and strictly between 0 and 1")
        self.reserve_fraction = float(self.reserve_fraction)
        self.guests = dict(self.guests)
        self.history = [dict(event) for event in self.history]
        self._validate_state()
        if self.history and not self.verify_history():
            raise AuditIntegrityError("preloaded audit history failed hash-chain validation")

    @property
    def reserve_mib(self) -> int:
        # Ceiling is deliberate: rounding may increase the reserve, never erode it.
        return max(1, math.ceil(self.total_mib * self.reserve_fraction))

    @property
    def allocated_mib(self) -> int:
        return sum(g.memory_mib for g in self.guests.values())

    @property
    def free_mib(self) -> int:
        return self.total_mib - self.reserve_mib - self.allocated_mib

    @property
    def audit_head(self) -> str:
        return self.history[-1]["event_hash"] if self.history else ZERO_HASH

    def _validate_state(self) -> None:
        seen_names: set[str] = set()
        for key, guest in self.guests.items():
            if not isinstance(guest, Guest):
                raise StateIntegrityError("guest registry contains a non-Guest value", key=key)
            if key != guest.name:
                raise StateIntegrityError(
                    "guest registry key does not match guest.name", key=key, guest=guest.name
                )
            if guest.name in seen_names:
                raise StateIntegrityError("duplicate guest identity", guest=guest.name)
            seen_names.add(guest.name)
        if self.allocated_mib > self.total_mib - self.reserve_mib:
            raise StateIntegrityError(
                "guest allocations cross the host reserve",
                allocated_mib=self.allocated_mib,
                allocatable_mib=self.total_mib - self.reserve_mib,
            )

    def _guest(self, name: str) -> Guest:
        _require_identifier("guest name", name)
        try:
            return self.guests[name]
        except KeyError as exc:
            raise UnknownGuest(f"{name}: guest is not present on {self.name}", guest=name, host=self.name) from exc

    def _operation_id(self, operation_id: str | None) -> str:
        if operation_id is None:
            return uuid4().hex
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if len(operation_id) > MAX_OPERATION_ID_LENGTH:
            raise ValueError(f"operation_id exceeds {MAX_OPERATION_ID_LENGTH} characters")
        return operation_id

    def _append_event(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        event = dict(payload)
        event["audit_schema"] = AUDIT_EVENT_SCHEMA
        event["sequence"] = len(self.history) + 1
        event["prev_hash"] = self.audit_head
        event["event_hash"] = _canonical_hash(event)
        self.history.append(event)
        # Do not let a caller mutate the copy held in the audit ledger.
        return dict(event)

    def verify_history(self) -> bool:
        previous = ZERO_HASH
        for index, stored in enumerate(self.history, start=1):
            if not isinstance(stored, dict):
                return False
            event = dict(stored)
            event_hash = event.pop("event_hash", None)
            if event.get("audit_schema") != AUDIT_EVENT_SCHEMA:
                return False
            if event.get("sequence") != index:
                return False
            if event.get("prev_hash") != previous:
                return False
            try:
                expected_hash = _canonical_hash(event)
            except (TypeError, ValueError):
                return False
            if not isinstance(event_hash, str) or event_hash != expected_hash:
                return False
            previous = event_hash
        return True

    def _require_clean_history(self) -> None:
        if not self.verify_history():
            raise AuditIntegrityError("audit history was modified or corrupted")

    def _find_operation(self, operation_id: str) -> dict[str, Any] | None:
        for event in reversed(self.history):
            if event.get("operation_id") == operation_id:
                return event
        return None

    def _replay(self, operation_id: str, fingerprint: Mapping[str, Any]) -> dict[str, Any] | None:
        existing = self._find_operation(operation_id)
        if existing is None:
            return None
        if all(existing.get(key) == value for key, value in fingerprint.items()):
            return dict(existing)
        raise ReplayConflict(
            f"operation_id {operation_id!r} was already used for a different operation",
            operation_id=operation_id,
        )

    def add(self, guest: Guest) -> Guest:
        if not isinstance(guest, Guest):
            raise TypeError("guest must be a Guest instance")
        with self._lock:
            self._require_clean_history()
            self._validate_state()
            if guest.name in self.guests:
                raise ValueError(f"{guest.name}: a guest with this name is already on {self.name}")
            if guest.memory_mib > self.free_mib:
                raise ReserveBreach(
                    f"{guest.name}: {guest.memory_mib}MiB exceeds {self.free_mib}MiB allocatable",
                    guest=guest.name,
                    requested_mib=guest.memory_mib,
                    free_mib=self.free_mib,
                )
            self.guests[guest.name] = guest
            self._append_event(
                {
                    "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                    "kind": "guest_add",
                    "operation_id": uuid4().hex,
                    "host": self.name,
                    "guest": guest.name,
                    "tenant": guest.tenant,
                    "applied_mib": guest.memory_mib,
                    "applied_vcpus": guest.vcpus,
                    "reason": "guest admitted within host reserve",
                }
            )
            return guest

    def remove(self, name: str) -> Guest:
        """Remove a guest and reclaim its allocation from this host."""
        with self._lock:
            self._require_clean_history()
            self._validate_state()
            guest = self._guest(name)
            del self.guests[name]
            self._free_page_reports.pop(name, None)
            self._append_event(
                {
                    "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                    "kind": "guest_remove",
                    "operation_id": uuid4().hex,
                    "host": self.name,
                    "guest": guest.name,
                    "tenant": guest.tenant,
                    "from_mib": guest.memory_mib,
                    "from_vcpus": guest.vcpus,
                    "reason": "guest removed from host",
                }
            )
            return guest

    def host_snapshot(self) -> dict[str, Any]:
        """Return the externally visible PK_HOST_RESOURCES/1 view."""
        with self._lock:
            self._require_clean_history()
            self._validate_state()
            return {
                "schema": HOST_RESOURCES_SCHEMA,
                "host": self.name,
                "total_mib": self.total_mib,
                "reserve_mib": self.reserve_mib,
                "allocated_mib": self.allocated_mib,
                "free_mib": self.free_mib,
                "guest_count": len(self.guests),
                "audit_head": self.audit_head,
            }

    def report_free_pages(self, name: str, free_mib: int) -> dict[str, Any]:
        """Record a bounded guest free-page report without treating it as reclaimed memory."""
        _require_int("free_mib", free_mib, minimum=0)
        with self._lock:
            self._require_clean_history()
            self._validate_state()
            guest = self._guest(name)
            if free_mib > guest.memory_mib:
                raise ValueError(
                    f"{name}: reported free pages ({free_mib}MiB) exceed allocated memory ({guest.memory_mib}MiB)"
                )
            self._free_page_reports[name] = free_mib
            return self._append_event(
                {
                    "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                    "kind": "free_page_report",
                    "operation_id": uuid4().hex,
                    "host": self.name,
                    "guest": name,
                    "tenant": guest.tenant,
                    "free_pages_mib": free_mib,
                    "reason": "guest reported reclaimable free pages",
                }
            )

    def adjust_memory(
        self,
        name: str,
        target_mib: int,
        *,
        honoured: bool = True,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        _require_int("target_mib", target_mib, minimum=0)
        if not isinstance(honoured, bool):
            raise TypeError("honoured must be a bool")
        operation_id = self._operation_id(operation_id)
        with self._lock:
            self._require_clean_history()
            self._validate_state()
            guest = self._guest(name)
            fingerprint = {
                "kind": "memory",
                "guest": name,
                "requested_mib": target_mib,
                "honoured_requested": honoured,
            }
            replay = self._replay(operation_id, fingerprint)
            if replay is not None:
                return replay

            previous = guest.memory_mib
            if target_mib < guest.floor_mib:
                raise FloorBreach(
                    f"{name}: {target_mib}MiB is below its {guest.floor_mib}MiB working-set floor",
                    guest=name,
                    target_mib=target_mib,
                    floor_mib=guest.floor_mib,
                )
            target = min(target_mib, guest.ceiling_mib)
            delta = target - previous
            if delta > self.free_mib:
                raise ReserveBreach(
                    f"{name}: growing by {delta}MiB would take {delta - self.free_mib}MiB from the reserve",
                    guest=name,
                    delta_mib=delta,
                    free_mib=self.free_mib,
                )

            # Balloon reclaim is cooperative; growth does not depend on a balloon
            # driver returning pages, but the caller can still report a failed apply.
            effectively_honoured = honoured and (guest.cooperative or target >= previous)
            applied = target if effectively_honoured else previous
            self.guests[name] = replace(guest, memory_mib=applied)
            if applied != previous:
                # Free-page reports describe a prior allocation and become stale
                # after any successful resize; require a fresh guest report.
                self._free_page_reports.pop(name, None)
            record = self._append_event(
                {
                    "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                    "kind": "memory",
                    "operation_id": operation_id,
                    "host": self.name,
                    "guest": name,
                    "tenant": guest.tenant,
                    "from_mib": previous,
                    "requested_mib": target_mib,
                    "target_mib": target,
                    "applied_mib": applied,
                    "honoured_requested": honoured,
                    "honoured": effectively_honoured,
                    "clamped_to_ceiling": target != target_mib,
                    "reversible_to": previous,
                    "host_free_mib": self.free_mib,
                    "reason": "memory adjustment applied" if effectively_honoured else "guest did not honour reclaim",
                }
            )
            return record

    def adjust_vcpus(
        self, name: str, target: int, *, operation_id: str | None = None
    ) -> dict[str, Any]:
        _require_int("target", target, minimum=1)
        operation_id = self._operation_id(operation_id)
        with self._lock:
            self._require_clean_history()
            self._validate_state()
            guest = self._guest(name)
            fingerprint = {"kind": "vcpu", "guest": name, "requested_vcpus": target}
            replay = self._replay(operation_id, fingerprint)
            if replay is not None:
                return replay
            if target > guest.vcpu_max:
                raise ValueError(f"{name}: {target} vCPUs outside [1, {guest.vcpu_max}]")
            previous = guest.vcpus
            self.guests[name] = replace(guest, vcpus=target)
            return self._append_event(
                {
                    "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                    "kind": "vcpu",
                    "operation_id": operation_id,
                    "host": self.name,
                    "guest": name,
                    "tenant": guest.tenant,
                    "from_vcpus": previous,
                    "requested_vcpus": target,
                    "applied_vcpus": target,
                    "reversible_to": previous,
                    "reason": "vCPU adjustment applied",
                }
            )

    def _trusted_v2_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if not self.verify_history():
            raise AuditIntegrityError("audit history was modified or corrupted")
        event_hash = record.get("event_hash")
        if not isinstance(event_hash, str):
            raise InvalidAdjustmentRecord("v2 adjustment record has no event_hash")
        for event in self.history:
            if event.get("event_hash") == event_hash:
                if dict(event) != dict(record):
                    raise InvalidAdjustmentRecord("adjustment record does not match the audited event")
                return dict(event)
        raise InvalidAdjustmentRecord("adjustment record is not present in this host's audit history")

    def revert(self, record: Mapping[str, Any], *, operation_id: str | None = None) -> int:
        """Revert a memory or vCPU adjustment after validating origin and freshness.

        Version-2 records must be byte-for-byte equivalent to an event in this
        host's verified audit chain.  Legacy v1 records are accepted for backward
        compatibility, but are constrained by current state, guest bounds and
        reserve checks because they predate authenticated host/operation metadata.
        """
        if not isinstance(record, Mapping):
            raise InvalidAdjustmentRecord("record must be a mapping")
        schema = record.get("schema")
        if schema not in {RESOURCE_ADJUSTMENT_SCHEMA, LEGACY_RESOURCE_ADJUSTMENT_SCHEMA}:
            raise InvalidAdjustmentRecord("unsupported or missing adjustment schema", schema=schema)

        with self._lock:
            self._validate_state()
            trusted = self._trusted_v2_record(record) if schema == RESOURCE_ADJUSTMENT_SCHEMA else dict(record)
            if trusted.get("host") not in {None, self.name}:
                raise InvalidAdjustmentRecord("adjustment belongs to another host", host=trusted.get("host"))
            name = trusted.get("guest")
            if not isinstance(name, str):
                raise InvalidAdjustmentRecord("adjustment record has no valid guest")
            guest = self._guest(name)

            kind = trusted.get("kind")
            if kind is None:  # v1 compatibility: infer from mutually exclusive fields.
                if "applied_mib" in trusted and "from_mib" in trusted:
                    kind = "memory"
                elif "applied_vcpus" in trusted and "from_vcpus" in trusted:
                    kind = "vcpu"
                else:
                    raise InvalidAdjustmentRecord("legacy adjustment type cannot be inferred safely")
            if kind not in {"memory", "vcpu"}:
                raise InvalidAdjustmentRecord(f"record kind {kind!r} is not reversible")

            revert_id = self._operation_id(operation_id)
            original_hash = trusted.get("event_hash")
            fingerprint = {
                "kind": f"{kind}_revert",
                "guest": name,
                "reverted_event_hash": original_hash,
            }
            replay = self._replay(revert_id, fingerprint)
            if replay is not None:
                return int(replay["applied_mib"] if kind == "memory" else replay["applied_vcpus"])

            try:
                target = trusted["reversible_to"]
            except KeyError as exc:
                raise InvalidAdjustmentRecord("adjustment has no reversible_to value") from exc
            _require_int("reversible_to", target, minimum=0 if kind == "memory" else 1)

            if kind == "memory":
                applied = trusted.get("applied_mib")
                _require_int("applied_mib", applied, minimum=0)
                if target < guest.floor_mib or target > guest.ceiling_mib:
                    raise InvalidAdjustmentRecord(
                        "revert target is outside the guest's current memory bounds",
                        target_mib=target,
                        floor_mib=guest.floor_mib,
                        ceiling_mib=guest.ceiling_mib,
                    )
                if guest.memory_mib == target:
                    return guest.memory_mib
                if guest.memory_mib != applied:
                    raise StaleAdjustment(
                        "memory changed after the recorded adjustment; refusing stale rollback",
                        current_mib=guest.memory_mib,
                        recorded_applied_mib=applied,
                    )
                delta = target - guest.memory_mib
                if delta > self.free_mib:
                    raise ReserveBreach(
                        f"{guest.name}: reverting would take {delta - self.free_mib}MiB from the reserve",
                        guest=guest.name,
                        delta_mib=delta,
                        free_mib=self.free_mib,
                    )
                previous = guest.memory_mib
                self.guests[name] = replace(guest, memory_mib=target)
                self._append_event(
                    {
                        "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                        "kind": "memory_revert",
                        "operation_id": revert_id,
                        "host": self.name,
                        "guest": name,
                        "tenant": guest.tenant,
                        "from_mib": previous,
                        "applied_mib": target,
                        "reverted_event_hash": original_hash,
                        "reason": "validated memory rollback",
                    }
                )
                return target

            applied = trusted.get("applied_vcpus")
            _require_int("applied_vcpus", applied, minimum=1)
            if not 1 <= target <= guest.vcpu_max:
                raise InvalidAdjustmentRecord(
                    "revert target is outside the guest's current vCPU bounds",
                    target_vcpus=target,
                    vcpu_max=guest.vcpu_max,
                )
            if guest.vcpus == target:
                return guest.vcpus
            if guest.vcpus != applied:
                raise StaleAdjustment(
                    "vCPU count changed after the recorded adjustment; refusing stale rollback",
                    current_vcpus=guest.vcpus,
                    recorded_applied_vcpus=applied,
                )
            previous = guest.vcpus
            self.guests[name] = replace(guest, vcpus=target)
            self._append_event(
                {
                    "schema": RESOURCE_ADJUSTMENT_SCHEMA,
                    "kind": "vcpu_revert",
                    "operation_id": revert_id,
                    "host": self.name,
                    "guest": name,
                    "tenant": guest.tenant,
                    "from_vcpus": previous,
                    "applied_vcpus": target,
                    "reverted_event_hash": original_hash,
                    "reason": "validated vCPU rollback",
                }
            )
            return target
