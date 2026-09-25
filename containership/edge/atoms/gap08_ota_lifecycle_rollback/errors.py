"""GAP-08 machine-readable error taxonomy (checklist component 21).

Every error raised by the GAP-08 control plane carries a stable code, a
retryability class, the affected resource, an optional causal chain and an
operator remediation hint.  Codes are part of the external contract
(``PK_ERROR/1``): they may be added, never renumbered or repurposed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

ERROR_SCHEMA = "PK_ERROR/1"


class Retry(str, Enum):
    NEVER = "never"            # terminal; retrying cannot help
    SAFE = "safe"              # idempotent; retry with backoff
    AFTER_REFRESH = "after_refresh"  # re-read state/lease/evidence first
    UNKNOWN_OUTCOME = "unknown_outcome"  # must reconcile before retry


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    retry: Retry
    remediation: str


# Stable registry.  Keep sorted by code; never reuse a retired code.
REGISTRY: dict[str, ErrorSpec] = {s.code: s for s in [
    ErrorSpec("GAP08-E001-VALIDATION", Retry.NEVER, "Fix the request payload; see `detail`."),
    ErrorSpec("GAP08-E002-DEPENDENCY_UNAVAILABLE", Retry.SAFE, "Check the named dependency; mutations stay blocked (fail-closed)."),
    ErrorSpec("GAP08-E003-CONFLICT", Retry.AFTER_REFRESH, "Another rollout or writer owns the resource; re-read and retry or wait."),
    ErrorSpec("GAP08-E004-TIMEOUT", Retry.UNKNOWN_OUTCOME, "Outcome unknown; run reconciliation before retrying."),
    ErrorSpec("GAP08-E005-STALE_REVISION", Retry.AFTER_REFRESH, "State changed under you; reload the latest revision."),
    ErrorSpec("GAP08-E006-STALE_FENCE", Retry.NEVER, "This controller lost its lease; stop and let the current holder proceed."),
    ErrorSpec("GAP08-E007-UNAUTHORIZED", Retry.NEVER, "Caller lacks the capability; request it through the authorization policy."),
    ErrorSpec("GAP08-E008-INTEGRITY", Retry.NEVER, "Stored state or audit chain failed verification; open a security incident."),
    ErrorSpec("GAP08-E009-EVIDENCE_REJECTED", Retry.AFTER_REFRESH, "Evidence was stale, replayed, unsigned or mis-bound; obtain fresh evidence."),
    ErrorSpec("GAP08-E010-POLICY_DENIED", Retry.AFTER_REFRESH, "Topology, window, freeze or admission policy denied the action; see `detail`."),
    ErrorSpec("GAP08-E011-FROZEN", Retry.NEVER, "An emergency freeze is active; an authorized operator must lift it."),
    ErrorSpec("GAP08-E012-ARTIFACT_MISMATCH", Retry.NEVER, "Downloaded bytes do not match the verified digest; quarantine the artifact."),
    ErrorSpec("GAP08-E013-IDENTITY", Retry.NEVER, "Device identity or attestation failed; investigate the node."),
    ErrorSpec("GAP08-E014-DUPLICATE", Retry.NEVER, "Command already processed; the stored result was returned."),
    ErrorSpec("GAP08-E015-OVERLOADED", Retry.SAFE, "Admission control shed load; retry after `retry_after_s`."),
    ErrorSpec("GAP08-E016-ILLEGAL_TRANSITION", Retry.NEVER, "The rollout's lifecycle state does not allow this operation."),
    ErrorSpec("GAP08-E017-INCOMPATIBLE", Retry.NEVER, "Compatibility matrix rejects this combination."),
    ErrorSpec("GAP08-E018-CIRCUIT_OPEN", Retry.SAFE, "Circuit breaker open for this cohort; wait for half-open probe."),
]}


class Gap08Error(RuntimeError):
    """Base error carrying a PK_ERROR/1 envelope."""

    code = "GAP08-E001-VALIDATION"

    def __init__(self, detail: str, *, resource: str | None = None, cause: BaseException | None = None,
                 code: str | None = None, **extra: Any) -> None:
        super().__init__(detail)
        if code is not None:
            self.code = code
        if self.code not in REGISTRY:
            raise KeyError(f"unregistered error code {self.code}")
        self.detail = detail
        self.resource = resource
        self.extra = extra
        if cause is not None:
            self.__cause__ = cause

    @property
    def spec(self) -> ErrorSpec:
        return REGISTRY[self.code]

    def to_dict(self) -> dict[str, Any]:
        chain = []
        cur = self.__cause__
        while cur is not None and len(chain) < 8:
            chain.append({"type": type(cur).__name__, "code": getattr(cur, "code", None), "detail": str(cur)})
            cur = cur.__cause__
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "retry": self.spec.retry.value,
            "resource": self.resource,
            "detail": self.detail,
            "remediation": self.spec.remediation,
            "causes": chain,
            **({"extra": self.extra} if self.extra else {}),
        }


def _make(name: str, code: str) -> type[Gap08Error]:
    return type(name, (Gap08Error,), {"code": code, "__doc__": REGISTRY[code].remediation})


ValidationFailed = _make("ValidationFailed", "GAP08-E001-VALIDATION")
DependencyUnavailable = _make("DependencyUnavailable", "GAP08-E002-DEPENDENCY_UNAVAILABLE")
Conflict = _make("Conflict", "GAP08-E003-CONFLICT")
Timeout = _make("Timeout", "GAP08-E004-TIMEOUT")
StaleRevision = _make("StaleRevision", "GAP08-E005-STALE_REVISION")
StaleFence = _make("StaleFence", "GAP08-E006-STALE_FENCE")
Unauthorized = _make("Unauthorized", "GAP08-E007-UNAUTHORIZED")
IntegrityFailure = _make("IntegrityFailure", "GAP08-E008-INTEGRITY")
EvidenceRejected = _make("EvidenceRejected", "GAP08-E009-EVIDENCE_REJECTED")
PolicyDenied = _make("PolicyDenied", "GAP08-E010-POLICY_DENIED")
Frozen = _make("Frozen", "GAP08-E011-FROZEN")
ArtifactMismatch = _make("ArtifactMismatch", "GAP08-E012-ARTIFACT_MISMATCH")
IdentityRejected = _make("IdentityRejected", "GAP08-E013-IDENTITY")
Duplicate = _make("Duplicate", "GAP08-E014-DUPLICATE")
Overloaded = _make("Overloaded", "GAP08-E015-OVERLOADED")
IllegalTransition = _make("IllegalTransition", "GAP08-E016-ILLEGAL_TRANSITION")
Incompatible = _make("Incompatible", "GAP08-E017-INCOMPATIBLE")
CircuitOpen = _make("CircuitOpen", "GAP08-E018-CIRCUIT_OPEN")

__all__ = ["ERROR_SCHEMA", "REGISTRY", "Retry", "ErrorSpec", "Gap08Error"] + [
    n for n in list(globals()) if isinstance(globals().get(n), type) and issubclass(globals()[n], Gap08Error)
    and n != "Gap08Error"
]
