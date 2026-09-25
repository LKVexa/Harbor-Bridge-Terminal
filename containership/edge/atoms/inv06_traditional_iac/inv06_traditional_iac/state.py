"""Hardened in-memory state engine for INV-06 Traditional IaC.

The engine models the safety properties needed by the master-applied component:
serial-bound plans, atomic apply, protected resources, drift detection, plan
integrity, structured errors, in-process concurrency control, basic metrics, and
a tamper-evident in-memory audit chain.

It intentionally does *not* pretend to be a durable or distributed state
backend.  Those production components are listed in ``MISSING_COMPONENTS.md``.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import hmac
import json
import math
import threading
import time
from typing import Any

PLAN_SCHEMA = "PK_IAC_PLAN/1"
STATE_SCHEMA = "PK_IAC_STATE/1"
DRIFT_SCHEMA = "PK_IAC_DRIFT/1"


class IacError(RuntimeError):
    """Base class for machine-readable IaC failures."""

    code = "PK_IAC_ERROR"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": deepcopy(self.details)}


class StalePlan(IacError):
    code = "PK_IAC_STALE_PLAN"


class ProtectedResource(IacError):
    code = "PK_IAC_PROTECTED_RESOURCE"


class InvalidPlan(IacError):
    code = "PK_IAC_INVALID_PLAN"


class InvalidState(IacError):
    code = "PK_IAC_INVALID_STATE"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _normalise_json(value: Any, *, path: str = "$", top_level_resource_map: bool = False) -> Any:
    """Return a detached JSON-compatible copy or fail closed.

    Traditional IaC state is represented as JSON-like data.  Restricting the
    reference engine to JSON-compatible values gives deterministic hashing and
    prevents aliasing of arbitrary caller-owned Python objects.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidState(f"non-finite number at {path}", details={"path": path})
        return value
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidState(
                    f"non-string object key at {path}",
                    details={"path": path, "key_type": type(key).__name__},
                )
            if top_level_resource_map and not key.strip():
                raise InvalidState("resource identifiers must be non-empty strings", details={"path": path})
            out[key] = _normalise_json(item, path=f"{path}.{key}")
        return out
    if isinstance(value, list):
        return [_normalise_json(item, path=f"{path}[{i}]") for i, item in enumerate(value)]
    raise InvalidState(
        f"unsupported state value at {path}: {type(value).__name__}",
        details={"path": path, "type": type(value).__name__},
    )


def _normalise_resource_map(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidState(f"{label} must be an object", details={"field": label})
    return _normalise_json(value, path=f"$.{label}", top_level_resource_map=True)


def _resource_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidState("resource identifier must be a non-empty string", details={"resource": value})
    return value


def _plan_payload(serial: int, create: Mapping[str, Any], update: Mapping[str, Any], delete: list[str]) -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "serial": serial,
        "create": create,
        "update": update,
        "delete": delete,
    }


def _plan_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class IacState:
    """Thread-safe reference state machine for plan/apply semantics.

    ``resources`` and ``protected`` are exposed as detached/read-only snapshots;
    callers cannot mutate authoritative state without going through methods that
    preserve serial and audit invariants.
    """

    def __init__(
        self,
        resources: Mapping[str, Any] | None = None,
        serial: int = 0,
        protected: set[str] | frozenset[str] | list[str] | tuple[str, ...] | None = None,
        audit_capacity: int = 4096,
    ) -> None:
        if isinstance(serial, bool) or not isinstance(serial, int) or serial < 0:
            raise InvalidState("serial must be a non-negative integer", details={"serial": serial})
        if isinstance(audit_capacity, bool) or not isinstance(audit_capacity, int) or audit_capacity < 1:
            raise InvalidState("audit_capacity must be a positive integer", details={"audit_capacity": audit_capacity})
        if protected is None:
            protected_items = ()
        elif isinstance(protected, (set, frozenset, list, tuple)):
            protected_items = protected
        else:
            raise InvalidState(
                "protected must be a set/list/tuple of resource identifiers",
                details={"type": type(protected).__name__},
            )
        self._lock = threading.RLock()
        self._resources = _normalise_resource_map(resources if resources is not None else {}, label="resources")
        self._serial = serial
        self._protected = {_resource_id(x) for x in protected_items}
        self._audit_capacity = audit_capacity
        self._metrics = {
            "plans": 0,
            "applies": 0,
            "stale_refusals": 0,
            "protected_refusals": 0,
            "invalid_plan_refusals": 0,
            "drift_scans": 0,
            "drifted": 0,
            "audit_dropped": 0,
        }
        self._audit: list[dict[str, Any]] = []
        self._audit_head = "0" * 64
        self._audit_anchor_digest = "0" * 64
        self._audit_anchor_seq = 0
        self._audit_count = 0
        self._record_event("state_initialized", {"resource_count": len(self._resources)})

    @property
    def serial(self) -> int:
        with self._lock:
            return self._serial

    @property
    def resources(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._resources)

    @property
    def protected(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._protected)

    def _record_event(self, action: str, details: Mapping[str, Any]) -> None:
        event = {
            "seq": self._audit_count + 1,
            "time_ns": time.time_ns(),
            "action": action,
            "serial": self._serial,
            "details": _normalise_json(dict(details), path="$.audit.details"),
            "previous_digest": self._audit_head,
        }
        digest = hashlib.sha256(_canonical_bytes(event)).hexdigest()
        event["digest"] = digest
        self._audit.append(event)
        self._audit_count += 1
        self._audit_head = digest
        if len(self._audit) > self._audit_capacity:
            dropped = self._audit.pop(0)
            self._audit_anchor_digest = dropped["digest"]
            self._audit_anchor_seq = dropped["seq"]
            self._metrics["audit_dropped"] += 1

    def audit_events(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._audit)

    def verify_audit_chain(self) -> bool:
        with self._lock:
            previous = self._audit_anchor_digest
            expected_seq = self._audit_anchor_seq + 1
            for event in self._audit:
                if event.get("seq") != expected_seq or event.get("previous_digest") != previous:
                    return False
                body = {k: deepcopy(v) for k, v in event.items() if k != "digest"}
                digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
                if digest != event.get("digest"):
                    return False
                previous = digest
                expected_seq += 1
            return previous == self._audit_head

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._metrics)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema": STATE_SCHEMA,
                "serial": self._serial,
                "resources": deepcopy(self._resources),
                "protected": sorted(self._protected),
                "audit_head": self._audit_head,
            }

    def protect(self, resource: str) -> int:
        resource = _resource_id(resource)
        with self._lock:
            if resource not in self._protected:
                self._protected.add(resource)
                # Protection policy is authoritative state.  Advancing the serial
                # invalidates any plan computed under the previous protection set.
                self._serial += 1
                self._record_event("resource_protected", {"resource": resource})
            return self._serial

    def unprotect(self, resource: str) -> int:
        resource = _resource_id(resource)
        with self._lock:
            if resource in self._protected:
                self._protected.remove(resource)
                self._serial += 1
                self._record_event("resource_unprotected", {"resource": resource})
            return self._serial

    def plan(self, desired: Mapping[str, Any]) -> dict[str, Any]:
        desired_copy = _normalise_resource_map(desired, label="desired")
        with self._lock:
            cur = self._resources
            create = {k: deepcopy(v) for k, v in desired_copy.items() if k not in cur}
            update = {k: deepcopy(v) for k, v in desired_copy.items() if k in cur and cur[k] != v}
            delete = sorted(k for k in cur if k not in desired_copy)
            blocked = sorted(k for k in delete if k in self._protected)
            if blocked:
                self._metrics["protected_refusals"] += 1
                self._record_event("plan_refused_protected", {"resources": blocked})
                raise ProtectedResource(
                    f"plan would destroy protected {blocked}",
                    details={"resources": blocked, "phase": "plan"},
                )
            payload = _plan_payload(self._serial, create, update, delete)
            plan = dict(payload)
            plan["integrity"] = {"algorithm": "sha256", "digest": _plan_digest(payload)}
            self._metrics["plans"] += 1
            self._record_event(
                "plan_created",
                {"create": sorted(create), "update": sorted(update), "delete": delete},
            )
            return deepcopy(plan)

    @staticmethod
    def _validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(plan, Mapping):
            raise InvalidPlan("plan must be an object", details={"type": type(plan).__name__})
        allowed = {"schema", "serial", "create", "update", "delete", "integrity"}
        missing = sorted({"schema", "serial", "create", "update", "delete", "integrity"} - set(plan))
        unknown = sorted(set(plan) - allowed)
        if missing or unknown:
            raise InvalidPlan("plan fields are invalid", details={"missing": missing, "unknown": unknown})
        if plan.get("schema") != PLAN_SCHEMA:
            raise InvalidPlan(
                "unsupported plan schema",
                details={"expected": PLAN_SCHEMA, "actual": plan.get("schema")},
            )
        serial = plan.get("serial")
        if isinstance(serial, bool) or not isinstance(serial, int) or serial < 0:
            raise InvalidPlan("plan serial must be a non-negative integer", details={"serial": serial})
        try:
            create = _normalise_resource_map(plan.get("create"), label="create")
            update = _normalise_resource_map(plan.get("update"), label="update")
        except InvalidState as exc:
            raise InvalidPlan(str(exc), details=exc.details) from exc
        delete_value = plan.get("delete")
        if not isinstance(delete_value, list):
            raise InvalidPlan("plan delete must be an array", details={"field": "delete"})
        try:
            delete = [_resource_id(x) for x in delete_value]
        except InvalidState as exc:
            raise InvalidPlan(str(exc), details=exc.details) from exc
        if len(delete) != len(set(delete)):
            raise InvalidPlan("plan delete contains duplicate resource identifiers")
        overlap = {
            "create_update": sorted(set(create) & set(update)),
            "create_delete": sorted(set(create) & set(delete)),
            "update_delete": sorted(set(update) & set(delete)),
        }
        if any(overlap.values()):
            raise InvalidPlan("plan operations overlap", details=overlap)
        integrity = plan.get("integrity")
        if not isinstance(integrity, Mapping) or integrity.get("algorithm") != "sha256":
            raise InvalidPlan("plan integrity metadata is missing or unsupported")
        digest = integrity.get("digest")
        if not isinstance(digest, str) or len(digest) != 64:
            raise InvalidPlan("plan digest is malformed")
        payload = _plan_payload(serial, create, update, delete)
        actual = _plan_digest(payload)
        if not hmac.compare_digest(digest.lower(), actual):
            raise InvalidPlan(
                "plan integrity verification failed",
                details={"expected_digest": actual, "supplied_digest": digest.lower()},
            )
        result = dict(payload)
        result["integrity"] = {"algorithm": "sha256", "digest": actual}
        return result

    def apply(self, plan: Mapping[str, Any]) -> int:
        try:
            p = self._validate_plan(plan)
        except InvalidPlan:
            with self._lock:
                self._metrics["invalid_plan_refusals"] += 1
                self._record_event("apply_refused_invalid_plan", {})
            raise

        with self._lock:
            self._check_applicable(p)

            # Build the entire next state before committing it.  Any validation or
            # copy failure occurs before the authoritative reference is replaced.
            next_resources = deepcopy(self._resources)
            next_resources.update(deepcopy(p["create"]))
            next_resources.update(deepcopy(p["update"]))
            for key in p["delete"]:
                del next_resources[key]

            self._resources = next_resources
            self._serial += 1
            self._metrics["applies"] += 1
            self._record_event(
                "plan_applied",
                {
                    "create": sorted(p["create"]),
                    "update": sorted(p["update"]),
                    "delete": sorted(p["delete"]),
                },
            )
            return self._serial

    def precheck(self, plan: Mapping[str, Any]) -> dict[str, Any]:
        """Run every apply-time check without mutating state (used before touching providers)."""
        try:
            p = self._validate_plan(plan)
        except InvalidPlan:
            with self._lock:
                self._metrics["invalid_plan_refusals"] += 1
                self._record_event("precheck_refused_invalid_plan", {})
            raise
        with self._lock:
            self._check_applicable(p)
        return p

    def _check_applicable(self, p: Mapping[str, Any]) -> None:
        if p["serial"] != self._serial:
            self._metrics["stale_refusals"] += 1
            self._record_event(
                "apply_refused_stale",
                {"plan_serial": p["serial"], "state_serial": self._serial},
            )
            raise StalePlan(
                f"plan made at serial {p['serial']}, state is at {self._serial}",
                details={"plan_serial": p["serial"], "state_serial": self._serial},
            )

        blocked = sorted(k for k in p["delete"] if k in self._protected)
        if blocked:
            self._metrics["protected_refusals"] += 1
            self._record_event("apply_refused_protected", {"resources": blocked})
            raise ProtectedResource(
                f"plan would destroy protected {blocked}",
                details={"resources": blocked, "phase": "apply"},
            )

        missing = sorted(k for k in list(p["delete"]) + list(p["update"]) if k not in self._resources)
        existing = sorted(k for k in p["create"] if k in self._resources)
        if missing or existing:
            self._metrics["stale_refusals"] += 1
            self._record_event(
                "apply_refused_state_mismatch",
                {"missing": missing, "already_present": existing},
            )
            raise StalePlan(
                f"plan does not match state (missing {missing}, already present {existing})",
                details={"missing": missing, "already_present": existing},
            )

    def drift(self, real: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        real_copy = _normalise_resource_map(real, label="real")
        with self._lock:
            keys = set(real_copy) | set(self._resources)
            out: dict[str, dict[str, Any]] = {}
            for key in sorted(keys):
                state_present = key in self._resources
                real_present = key in real_copy
                state_value = deepcopy(self._resources[key]) if state_present else None
                real_value = deepcopy(real_copy[key]) if real_present else None
                if state_present != real_present or state_value != real_value:
                    out[key] = {
                        "schema": DRIFT_SCHEMA,
                        "state": state_value,
                        "real": real_value,
                        "state_present": state_present,
                        "real_present": real_present,
                    }
            self._metrics["drift_scans"] += 1
            self._metrics["drifted"] = len(out)
            self._record_event("drift_scanned", {"drift_count": len(out), "resources": sorted(out)})
            return out
