"""MC-020 — adapters for the contract neighbours (PLN-04, GAP-13, GAP-09).

These are the INV-39 side of each interface.  Tests exercise them against
reference stubs that implement the neighbours' published obligations from the
contract; interoperability with the *real* neighbour builds is a separate
certification step (TRACEABILITY.json: MC-020 = PARTIAL until run).
"""
from __future__ import annotations

from typing import Any

from .errors import SandboxError
from .sandbox import SandboxProfile

TRUSTED_CLASSES = frozenset({"trusted", "first-party"})


def pln04_admit(workload: dict[str, Any]) -> None:
    """PLN-04 admits only trusted-class workloads to this tier; enforce it on our side too."""
    cls = workload.get("trust_class")
    if cls not in TRUSTED_CLASSES:
        raise SandboxError("E_PROFILE_INVALID",
                           f"trust class {cls!r} is not admissible to the process tier; route to microVM/VM tier")


def gap13_profile(policy: dict[str, Any]) -> SandboxProfile:
    """Convert a GAP-13 policy decision document into a canonical profile."""
    if policy.get("kind") != "sandbox-profile" or policy.get("decision") != "allow":
        raise SandboxError("E_PROFILE_INVALID", "GAP-13 did not issue an allow decision for a sandbox profile")
    body = policy.get("profile") or {}
    try:
        return SandboxProfile(body["name"], frozenset(body["syscalls"]), frozenset(body.get("capabilities", ())),
                              frozenset(body["namespaces"]))
    except KeyError as e:
        raise SandboxError("E_SCHEMA_INVALID", f"GAP-13 profile lacks {e}") from None


def gap09_export(service) -> dict[str, Any]:
    """Signals for GAP-09 unified observability: metrics text + status + audit head."""
    return {"metrics": service.metrics.exposition(), "status": service.status(),
            "audit_head": service.audit.head, "log_tail": list(service.log.lines)[-100:]}
