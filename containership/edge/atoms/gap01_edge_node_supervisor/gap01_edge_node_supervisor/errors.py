"""Structured error model (checklist component 25).

Every error the supervisor surfaces externally carries a stable machine code,
a retryability flag, a fault domain and operator-safe text.  Internal detail
(``detail``) is never serialised to callers unless explicitly requested by a
diagnostic path with redaction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# code -> (retryable, fault_domain, operator-safe text)
ERROR_CATALOG: dict[str, tuple[bool, str, str]] = {
    "E_BAD_REQUEST": (False, "caller", "request is malformed or fails schema validation"),
    "E_UNAUTHENTICATED": (False, "caller", "caller could not be authenticated"),
    "E_REPLAY": (False, "caller", "request nonce or id was already used"),
    "E_STALE_REQUEST": (True, "caller", "request timestamp outside the accepted window"),
    "E_FORBIDDEN": (False, "policy", "caller lacks the capability for this operation"),
    "E_ILLEGAL_TRANSITION": (False, "lifecycle", "requested lifecycle transition is not legal"),
    "E_DRAIN_INCOMPLETE": (True, "lifecycle", "node still has resident workloads"),
    "E_NOT_ACCEPTING": (True, "lifecycle", "node is not accepting placement"),
    "E_DUPLICATE_WORKLOAD": (False, "caller", "workload identity already admitted"),
    "E_UNKNOWN_WORKLOAD": (False, "caller", "workload identity is not resident"),
    "E_RATE_LIMITED": (True, "capacity", "request rate exceeded; retry later"),
    "E_CAPACITY": (True, "capacity", "a configured capacity ceiling was reached"),
    "E_EMERGENCY": (True, "safety", "supervisor is in fail-safe emergency mode"),
    "E_DISABLED": (False, "safety", "supervisor component is emergency-disabled"),
    "E_PARTITIONED": (True, "control-plane", "operation not permitted while partitioned"),
    "E_RUNTIME": (True, "runtime", "workload runtime adapter reported a failure"),
    "E_ISOLATION_UNPROVEN": (True, "runtime", "termination/reclaim of workload not proven"),
    "E_STATE_CORRUPT": (False, "persistence", "persisted state failed integrity checks"),
    "E_PERSISTENCE": (True, "persistence", "state could not be durably persisted"),
    "E_CONFIG": (False, "config", "configuration failed validation"),
    "E_SIGNATURE": (False, "integrity", "artifact or config signature invalid"),
    "E_MIGRATION": (False, "persistence", "state schema migration not possible"),
    "E_BOOTSTRAP": (True, "bootstrap", "bootstrap phase failed"),
    "E_INTERNAL": (True, "supervisor", "internal supervisor error"),
}


@dataclass
class SupervisorError(Exception):
    code: str
    detail: str = ""
    cause: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.code not in ERROR_CATALOG:
            self.detail = f"unknown code {self.code!r}: {self.detail}"
            self.code = "E_INTERNAL"
        Exception.__init__(self, f"{self.code}: {self.detail}")

    @property
    def retryable(self) -> bool:
        return ERROR_CATALOG[self.code][0]

    @property
    def fault_domain(self) -> str:
        return ERROR_CATALOG[self.code][1]

    def to_dict(self, *, include_detail: bool = False) -> dict[str, Any]:
        retryable, domain, text = ERROR_CATALOG[self.code]
        out: dict[str, Any] = {
            "code": self.code,
            "retryable": retryable,
            "fault_domain": domain,
            "message": text,
        }
        if self.cause:
            out["cause"] = self.cause
        if include_detail and self.detail:
            out["detail"] = self.detail[:512]
        return out


def wrap(exc: BaseException) -> SupervisorError:
    """Map legacy/core exceptions to the structured model."""
    from .supervisor import DrainIncomplete, IllegalTransition

    if isinstance(exc, SupervisorError):
        return exc
    if isinstance(exc, DrainIncomplete):
        return SupervisorError("E_DRAIN_INCOMPLETE", str(exc))
    if isinstance(exc, IllegalTransition):
        msg = str(exc)
        code = "E_NOT_ACCEPTING" if "does not accept placement" in msg else "E_ILLEGAL_TRANSITION"
        return SupervisorError(code, msg)
    if isinstance(exc, (ValueError, TypeError)):
        msg = str(exc)
        if "already admitted" in msg:
            return SupervisorError("E_DUPLICATE_WORKLOAD", msg)
        return SupervisorError("E_BAD_REQUEST", msg)
    return SupervisorError("E_INTERNAL", f"{type(exc).__name__}", cause=type(exc).__name__)
