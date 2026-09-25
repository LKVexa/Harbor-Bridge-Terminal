"""Core transient-execution policy model for INV-43.

This module is deliberately free of ``pk_core`` imports so the security-critical
policy logic can be tested in isolation.  The registry adapter lives in
``component.py``.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Iterable

ELEMENT_ID = "INV-43"
ELEMENT_NAME = "Transient-execution defense"

ACTIVE, INACTIVE, UNKNOWN = "active", "inactive", "unknown"
#: 4.3.0: the node reads back "Not affected" - the CPU does not carry the flaw,
#: so no mitigation is needed and none is paid for.  Only representable in
#: PK_MITIGATIONS/2; a v1 consumer is refused rather than shown a lie.
NOT_AFFECTED = "not_affected"
VALID_STATUSES = frozenset({ACTIVE, INACTIVE, UNKNOWN, NOT_AFFECTED})
SATISFYING_STATUSES = frozenset({ACTIVE, NOT_AFFECTED})
V1_STATUSES = frozenset({ACTIVE, INACTIVE, UNKNOWN})

#: Baseline mitigations required before different tenants may share a node.
#: Callers may supply an explicit stricter set to :meth:`may_cotenant`.
REQUIRED_FOR_COTENANCY = ("spectre_v2", "l1tf", "mds", "mmio_stale_data")


class MitigationMissing(PermissionError):
    """Raised when a requested cross-tenant placement is not safe.

    ``code`` and ``details`` provide stable machine-readable context while the
    exception string remains useful to operators and existing callers.
    """

    def __init__(self, message: str, *, code: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})

    def to_dict(self) -> dict:
        return {
            "schema": "PK_ERROR/1",
            "code": self.code,
            "message": str(self),
            "details": dict(self.details),
        }


def _require_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{field_name} must not contain control characters")
    return value


def _normalise_required(required: Iterable[str] | None) -> tuple[str, ...]:
    if required is None:
        return REQUIRED_FOR_COTENANCY
    if isinstance(required, (str, bytes)):
        raise TypeError("required_mitigations must be an iterable of mitigation names")
    names: list[str] = []
    seen: set[str] = set()
    for raw in required:
        name = _require_identifier(raw, "required mitigation")
        if name not in seen:
            names.append(name)
            seen.add(name)
    if not names:
        raise ValueError("required_mitigations must not be empty for cross-tenant policy")
    return tuple(names)


@dataclass
class MitigationState:
    """One node's transient-execution posture, as read back rather than assumed.

    ``mitigations`` maps mitigation name to ``(status, measured_cost_percent)``.
    The tuple representation is retained for compatibility with 4.1.x callers.
    """

    node: str
    mitigations: dict[str, tuple[str, float]] = field(default_factory=dict)
    smt_enabled: bool = True
    core_scheduling: bool = False
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False, compare=False)

    # Concurrency contract (4.3.0): every public method takes ``_lock``; a
    # decision is evaluated against one consistent snapshot, never a half-written
    # record set.  See docs/CONCURRENCY.md.

    def __post_init__(self) -> None:
        self.node = _require_identifier(self.node, "node")
        if not isinstance(self.smt_enabled, bool):
            raise TypeError("smt_enabled must be bool")
        if not isinstance(self.core_scheduling, bool):
            raise TypeError("core_scheduling must be bool")

        supplied = dict(self.mitigations)
        self.mitigations = {}
        for name, record in supplied.items():
            if not isinstance(record, (tuple, list)) or len(record) != 2:
                raise ValueError(f"{name!r}: mitigation record must be (status, cost_percent)")
            self.record(name, record[0], record[1])

    def record(self, name: str, status: str, cost_percent: float = 0.0) -> None:
        """Record a node-read mitigation state after strict validation.

        Active mitigations require a positive measured cost.  Inactive/unknown
        states require zero cost so stale measurements cannot be mistaken for
        currently paid overhead.
        """
        name = _require_identifier(name, "mitigation name")
        if status not in VALID_STATUSES:
            raise ValueError(f"unknown mitigation status: {status!r}")
        if isinstance(cost_percent, bool) or not isinstance(cost_percent, (int, float)):
            raise TypeError(f"{name}: cost must be a real number, not {type(cost_percent).__name__}")
        cost = float(cost_percent)
        if not math.isfinite(cost) or cost < 0:
            raise ValueError(f"{name}: cost must be a finite non-negative percentage")
        if status == ACTIVE and cost <= 0:
            raise ValueError(f"{name}: an active mitigation must carry a measured cost")
        if status != ACTIVE and cost != 0:
            raise ValueError(f"{name}: inactive/unknown/not_affected mitigation cost must be zero")
        with self._lock:
            self.mitigations[name] = (status, cost)

    def snapshot(self) -> dict[str, tuple[str, float]]:
        with self._lock:
            return dict(self.mitigations)

    def status(self, name: str) -> str:
        """Return status; an unrecorded mitigation is always ``unknown``."""
        name = _require_identifier(name, "mitigation name")
        with self._lock:
            return self.mitigations.get(name, (UNKNOWN, 0.0))[0]

    def satisfied(self, name: str) -> bool:
        return self.status(name) in SATISFYING_STATUSES

    def active(self) -> set[str]:
        return {name for name, (status, _) in self.snapshot().items() if status == ACTIVE}

    def total_cost(self) -> float:
        return round(math.fsum(cost for status, cost in self.snapshot().values() if status == ACTIVE), 2)

    def report(self, required_mitigations: Iterable[str] | None = None, *, version: int = 1) -> dict:
        """Return the versioned status contract, including per-mitigation costs.

        ``version=1`` is the 4.2.x shape.  It cannot express ``not_affected``;
        rather than silently rewriting that status, a v1 report of such a node
        raises :class:`MitigationMissing` (code ``schema_version_unrepresentable``)
        so the caller must negotiate PK_MITIGATIONS/2.
        """
        required = _normalise_required(required_mitigations)
        snap = self.snapshot()
        if version not in (1, 2):
            raise ValueError(f"unsupported PK_MITIGATIONS version {version!r}")
        if version == 1 and any(st not in V1_STATUSES for st, _ in snap.values()):
            raise MitigationMissing(
                f"{self.node}: posture contains statuses PK_MITIGATIONS/1 cannot represent",
                code="schema_version_unrepresentable",
                details={"node": self.node, "requested": "PK_MITIGATIONS/1", "supported": ["PK_MITIGATIONS/2"]},
            )
        details = {
            name: {"status": status, "cost_percent": cost}
            for name, (status, cost) in sorted(snap.items())
        }
        body = {
            "schema": f"PK_MITIGATIONS/{version}",
            "node": self.node,
            "mitigations": details,
            "active": sorted(n for n, (st, _) in snap.items() if st == ACTIVE),
            "inactive_or_unknown": sorted(
                name for name in required if snap.get(name, (UNKNOWN, 0.0))[0] not in SATISFYING_STATUSES
            ),
            "required_for_cotenancy": list(required),
            "total_cost_percent": round(math.fsum(c for st, c in snap.values() if st == ACTIVE), 2),
            "smt_enabled": self.smt_enabled,
            "core_scheduling": self.core_scheduling,
        }
        if version == 2:
            body["not_affected"] = sorted(n for n, (st, _) in snap.items() if st == NOT_AFFECTED)
        return body

    def may_cotenant(
        self,
        tenant_a: str,
        tenant_b: str,
        required_mitigations: Iterable[str] | None = None,
    ) -> dict:
        """Authorize co-tenancy only when the caller's required set is active.

        Same-tenant placement does not cross the tenant boundary and therefore
        returns early.  Cross-tenant placement fails closed for any missing or
        unknown required mitigation and for SMT without core scheduling.
        """
        tenant_a = _require_identifier(tenant_a, "tenant_a")
        tenant_b = _require_identifier(tenant_b, "tenant_b")
        if tenant_a == tenant_b:
            return {
                "schema": "PK_COTENANCY/1",
                "permitted": True,
                "reason": "same tenant; no cross-tenant boundary to defend",
                "tenants": [tenant_a],
            }

        required = _normalise_required(required_mitigations)
        snap = self.snapshot()
        missing = [name for name in required if snap.get(name, (UNKNOWN, 0.0))[0] not in SATISFYING_STATUSES]
        if missing:
            raise MitigationMissing(
                f"{self.node}: cross-tenant co-tenancy needs {missing} active",
                code="required_mitigation_missing",
                details={"node": self.node, "missing": missing, "required": list(required)},
            )
        if self.smt_enabled and not self.core_scheduling:
            raise MitigationMissing(
                f"{self.node}: SMT is enabled without core scheduling; siblings share "
                "microarchitectural state across the tenant boundary",
                code="unsafe_smt",
                details={"node": self.node, "smt_enabled": True, "core_scheduling": False},
            )
        return {
            "schema": "PK_COTENANCY/1",
            "permitted": True,
            "tenants": sorted([tenant_a, tenant_b]),
            "mitigations": sorted(n for n, (st, _) in snap.items() if st == ACTIVE),
            "required_mitigations": list(required),
            "cost_percent": round(math.fsum(c for st, c in snap.values() if st == ACTIVE), 2),
        }
