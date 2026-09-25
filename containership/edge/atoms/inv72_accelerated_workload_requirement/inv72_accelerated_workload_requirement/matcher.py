"""Deterministic, fail-closed accelerator requirement matching for INV-72.

This module deliberately has no dependency on ``pk_core`` so the security-critical
matching logic can be imported and unit-tested in isolation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
import math
from numbers import Real
from typing import Any


# Documented bounds (C028, C067).  Anything larger is refused before any work is done,
# so memory and time per decision are bounded by these constants.
MAX_INVENTORY = 4096          # devices per decision
MAX_COUNT = 64                # devices per requirement
MAX_ID_LEN = 128              # characters in any identifier
MAX_TENANTS_PER_DEVICE = 64   # co-tenants recorded on one partition
MAX_MEM_GB = 1_000_000.0      # sanity ceiling; larger values are malformed, not large


class RequirementValidationError(ValueError):
    """Raised when an accelerator requirement is malformed or unsafe."""

    code = "ACCEL_INVALID_REQUIREMENT"


class InventoryValidationError(ValueError):
    """Raised when discovered accelerator inventory is malformed or ambiguous."""

    code = "ACCEL_INVALID_INVENTORY"


class LimitExceededError(ValueError):
    """Raised when a payload exceeds a documented bound (subclass of ValueError for compatibility)."""

    code = "ACCEL_LIMIT_EXCEEDED"


@dataclass(slots=True)
class Device:
    """A discovered accelerator or accelerator partition.

    ``partition_of`` is empty for a whole device and contains the physical-device
    identifier for a partition. ``tenants`` models current tenant ownership used by
    this reference matcher; production allocation ownership remains a scheduler
    concern, as stated by the component contract.
    """

    dev_id: str
    cls: str
    mem_gb: float
    node: str
    link_group: str
    partition_of: str = ""
    tenants: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        _validate_device(self)


def _nonempty_string(value: Any, field_name: str, error_type: type[ValueError]) -> str:
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"{field_name} must be a non-empty string")
    if len(value) > MAX_ID_LEN:
        raise LimitExceededError(f"{field_name} longer than {MAX_ID_LEN} characters")
    return value


def _finite_nonnegative_number(value: Any, field_name: str, error_type: type[ValueError]) -> float:
    # bool is an int subclass; accepting True as 1 GB or False as 0 GB is unsafe.
    if isinstance(value, bool) or not isinstance(value, Real):
        raise error_type(f"{field_name} must be a finite non-negative number")
    try:
        number = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise error_type(f"{field_name} must be a finite non-negative number") from exc
    if not math.isfinite(number) or number < 0 or number > MAX_MEM_GB:
        raise error_type(f"{field_name} must be a finite non-negative number")
    return number


def _validate_device(device: Device) -> None:
    if not isinstance(device, Device):
        raise InventoryValidationError("inventory entries must be Device instances")
    _nonempty_string(device.dev_id, "device.dev_id", InventoryValidationError)
    _nonempty_string(device.cls, "device.cls", InventoryValidationError)
    _finite_nonnegative_number(device.mem_gb, "device.mem_gb", InventoryValidationError)
    _nonempty_string(device.node, "device.node", InventoryValidationError)
    _nonempty_string(device.link_group, "device.link_group", InventoryValidationError)
    if not isinstance(device.partition_of, str):
        raise InventoryValidationError("device.partition_of must be a string")
    if device.partition_of and not device.partition_of.strip():
        raise InventoryValidationError("device.partition_of must be empty or a non-blank string")
    if len(device.partition_of) > MAX_ID_LEN:
        raise LimitExceededError(f"device.partition_of longer than {MAX_ID_LEN} characters")
    if not isinstance(device.tenants, set) or any(
        not isinstance(tenant, str) or not tenant.strip() for tenant in device.tenants
    ):
        raise InventoryValidationError("device.tenants must be a set of non-empty strings")
    if len(device.tenants) > MAX_TENANTS_PER_DEVICE or any(len(t) > MAX_ID_LEN for t in device.tenants):
        raise LimitExceededError("device.tenants exceeds documented bounds")


def _normalise_requirement(req: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(req, Mapping):
        raise RequirementValidationError("requirement must be a mapping")

    missing = [key for key in ("class", "mem_gb", "tenant") if key not in req]
    if missing:
        raise RequirementValidationError(f"requirement missing {', '.join(repr(k) for k in missing)}")

    cls = _nonempty_string(req["class"], "class", RequirementValidationError)
    tenant = _nonempty_string(req["tenant"], "tenant", RequirementValidationError)
    mem_gb = _finite_nonnegative_number(req["mem_gb"], "mem_gb", RequirementValidationError)

    count = req.get("count", 1)
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise RequirementValidationError("count must be a positive integer")
    if count > MAX_COUNT:
        raise LimitExceededError(f"count {count} exceeds MAX_COUNT {MAX_COUNT}")

    interconnect = req.get("interconnect", False)
    if not isinstance(interconnect, bool):
        raise RequirementValidationError("interconnect must be a boolean")

    # Missing isolation defaults to the more restrictive mode. Unknown values are
    # rejected instead of being treated as permission to use a partition.
    isolation = req.get("isolation", "dedicated")
    if not isinstance(isolation, str) or isolation not in {"dedicated", "shared"}:
        raise RequirementValidationError("isolation must be 'dedicated' or 'shared'")

    return {
        "class": cls,
        "mem_gb": mem_gb,
        "tenant": tenant,
        "count": count,
        "interconnect": interconnect,
        "isolation": isolation,
    }


def _normalise_inventory(devices: Iterable[Device]) -> list[Device]:
    if isinstance(devices, (str, bytes)):
        raise InventoryValidationError("devices must be an iterable of Device instances")
    try:
        inventory = []
        for device in devices:
            inventory.append(device)
            if len(inventory) > MAX_INVENTORY:
                raise LimitExceededError(f"inventory exceeds MAX_INVENTORY {MAX_INVENTORY}")
    except TypeError as exc:
        raise InventoryValidationError("devices must be an iterable of Device instances") from exc

    seen: set[str] = set()
    for device in inventory:
        _validate_device(device)
        if device.dev_id in seen:
            raise InventoryValidationError(f"duplicate device id {device.dev_id!r}")
        seen.add(device.dev_id)
    return inventory


def _fmt_gb(value: float) -> str:
    return f"{value:g}"


def decide(req: Mapping[str, Any], devices: Iterable[Device], *, reserve: bool = False,
           excluded: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Structured decision (PK_ACCEL_MATCH/1 detail form; C026, C076).

    Returns ``{"selected": [...] | None, "code": str | None, "reasons": [{"code", "device", "text"}],
    "rationale": [...], "requirement": {...}, "considered": int}``.  ``excluded`` maps device ids to an
    operator reason (quarantine/drain); excluded devices are never selected and the exclusion is explained.
    Validation errors raise exactly as :func:`match` does.
    """
    requirement = _normalise_requirement(req)
    inventory = _normalise_inventory(devices)
    excluded = dict(excluded or {})
    reasons: list[dict[str, Any]] = []
    rationale: list[str] = []

    def refuse(code: str, text: str) -> dict[str, Any]:
        reasons.append({"code": code, "device": None, "text": text})
        return {"selected": None, "code": code, "reasons": reasons, "rationale": rationale,
                "requirement": requirement, "considered": len(inventory)}

    candidates = sorted(
        (d for d in inventory if d.cls == requirement["class"]),
        key=lambda d: (d.node, d.link_group, d.dev_id),
    )
    if not candidates:
        return refuse("ACCEL_NO_CLASS", f"no {requirement['class']} devices")
    rationale.append(f"{len(candidates)} device(s) of class {requirement['class']}")

    fit = [d for d in candidates if float(d.mem_gb) >= requirement["mem_gb"]]
    if not fit:
        largest = max(float(d.mem_gb) for d in candidates)
        return refuse("ACCEL_INSUFFICIENT_MEMORY",
                      f"largest {requirement['class']} has {_fmt_gb(largest)} GB < "
                      f"{_fmt_gb(requirement['mem_gb'])} GB")
    rationale.append(f"{len(fit)} with >= {_fmt_gb(requirement['mem_gb'])} GB")

    eligible: list[Device] = []
    for device in fit:
        if device.dev_id in excluded:
            reasons.append({"code": "ACCEL_DEVICE_QUARANTINED", "device": device.dev_id,
                            "text": f"{device.dev_id}: excluded by operator ({excluded[device.dev_id]})"})
            continue
        if device.partition_of:
            if requirement["isolation"] != "shared":
                reasons.append({"code": "ACCEL_PARTITION_DEDICATED", "device": device.dev_id,
                                "text": f"{device.dev_id}: partition not allowed for dedicated isolation"})
                continue
            if device.tenants - {requirement["tenant"]}:
                reasons.append({"code": "ACCEL_PARTITION_FOREIGN_TENANT", "device": device.dev_id,
                                "text": f"{device.dev_id}: partition already shared with another tenant"})
                continue
        elif device.tenants - {requirement["tenant"]}:
            reasons.append({"code": "ACCEL_DEVICE_FOREIGN_TENANT", "device": device.dev_id,
                            "text": f"{device.dev_id}: whole device already assigned to another tenant"})
            continue
        eligible.append(device)
    rationale.append(f"{len(eligible)} eligible after isolation/ownership rules")

    count = requirement["count"]
    if requirement["interconnect"]:
        groups: dict[tuple[str, str], list[Device]] = {}
        for device in eligible:
            groups.setdefault((device.node, device.link_group), []).append(device)
        chosen_key = next((key for key, group in groups.items() if len(group) >= count), None)
        if chosen_key is None:
            return refuse("ACCEL_NO_INTERCONNECT", f"no {count} devices share one interconnect")
        chosen = groups[chosen_key][:count]
        rationale.append(f"first interconnect group in (node, link_group) order with >= {count}: "
                         f"{chosen_key[0]}/{chosen_key[1]}")
    else:
        if len(eligible) < count:
            return refuse("ACCEL_INSUFFICIENT_COUNT", f"only {len(eligible)} eligible device(s), need {count}")
        chosen = eligible[:count]
        rationale.append(f"first {count} eligible in (node, link_group, dev_id) order")

    if reserve:
        for device in chosen:
            device.tenants.add(requirement["tenant"])
    return {"selected": [d.dev_id for d in chosen], "code": None, "reasons": reasons,
            "rationale": rationale, "requirement": requirement, "considered": len(inventory)}


def match(req: Mapping[str, Any], devices: Iterable[Device], *, reserve: bool = True):
    """Match a requirement to eligible devices.

    Returns ``(device_ids, reasons)`` where ``device_ids`` is ``None`` on a clean
    non-match. Malformed requirements/inventory raise explicit validation errors.

    Selection is deterministic and independent of caller inventory order. When
    ``reserve`` is true (the backward-compatible default), the selected devices'
    tenant ownership is updated only after the full selection succeeds. Use
    ``reserve=False`` for a side-effect-free eligibility check.  :func:`decide`
    returns the same decision with stable reason codes and a selection rationale.
    """
    result = decide(req, devices, reserve=reserve)
    return result["selected"], [r["text"] for r in result["reasons"]]
