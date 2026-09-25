"""Stable reason-code registry for GAP-14 v4.3.0 (G14 B01/B02 for every component).

Every expected refusal or failure carries a code from this registry.  Each code
has a *category* (who is at fault) and a *disposition* (what the caller may do).
Codes are append-only: a code is never re-used with a different meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .engine import GravityDecisionError

# categories
CALLER = "caller"
DEPENDENCY = "dependency"
SECURITY = "security"
STALE = "stale-data"
INTERNAL = "internal"
POLICY = "policy"

# dispositions
FAIL_CLOSED = "fail-closed"
RETRYABLE = "retryable"
DEGRADABLE = "degradable"
OPERATOR = "operator-actionable"


@dataclass(frozen=True)
class ReasonCode:
    code: str
    category: str
    disposition: str
    summary: str
    operator_action: str


_CODES = [
    # engine (v4.2.0, retained)
    ReasonCode("PK_GRAVITY_NO_LEGAL_OPTION", POLICY, FAIL_CLOSED, "residency/capability leaves no legal option", "Inspect elimination_details; do not override residency."),
    ReasonCode("PK_GRAVITY_COST_MODEL_ERROR", DEPENDENCY, FAIL_CLOSED, "a legal option cannot be honestly costed", "Check topology/cost feed for the missing route."),
    # caller
    ReasonCode("G14_INVALID_REQUEST", CALLER, FAIL_CLOSED, "request failed strict validation", "Fix the payload; see details.field."),
    ReasonCode("G14_PAYLOAD_TOO_LARGE", CALLER, FAIL_CLOSED, "payload exceeds admission size bound", "Split the batch or raise limits via signed config."),
    # security
    ReasonCode("G14_UNAUTHENTICATED", SECURITY, FAIL_CLOSED, "no valid capability token", "Obtain a token from the identity service."),
    ReasonCode("G14_FORBIDDEN", SECURITY, FAIL_CLOSED, "principal lacks scope or tenant access", "Grant the scope in the identity service; never bypass."),
    ReasonCode("G14_CROSS_TENANT", SECURITY, FAIL_CLOSED, "workload tenant differs from dataset tenant", "Tenancy boundary is absolute; no action short of re-tenanting data."),
    ReasonCode("G14_SIGNATURE_INVALID", SECURITY, FAIL_CLOSED, "signature or MAC verification failed", "Check key distribution; treat as possible tampering."),
    ReasonCode("G14_UNKNOWN_ISSUER", SECURITY, FAIL_CLOSED, "issuer/key id not in trust store", "Rotate trust store via signed config."),
    ReasonCode("G14_BINDING_MISMATCH", SECURITY, FAIL_CLOSED, "artifact bound to a different request", "Possible replay; investigate the producer."),
    ReasonCode("G14_REPLAY", SECURITY, FAIL_CLOSED, "nonce/decision id already seen", "Possible replay; investigate."),
    ReasonCode("G14_VERSION_ROLLBACK", SECURITY, FAIL_CLOSED, "policy/config/snapshot version went backwards", "Confirm the authority's revision; reset watermark only by operator action."),
    # stale
    ReasonCode("G14_STALE_INPUT", STALE, FAIL_CLOSED, "decision input older than its TTL", "Refresh the producing service; check its health."),
    ReasonCode("G14_CLOCK_SKEW", STALE, FAIL_CLOSED, "artifact issued in the future beyond skew allowance", "Check NTP on producer and GAP-14 hosts."),
    # dependency
    ReasonCode("G14_DEPENDENCY_TIMEOUT", DEPENDENCY, RETRYABLE, "dependency exceeded its deadline", "Check dependency latency dashboards."),
    ReasonCode("G14_DEPENDENCY_UNAVAILABLE", DEPENDENCY, RETRYABLE, "dependency returned an error or is partitioned", "Check dependency health."),
    ReasonCode("G14_CIRCUIT_OPEN", DEPENDENCY, DEGRADABLE, "circuit breaker open for dependency", "Wait for half-open probe; fix dependency."),
    ReasonCode("G14_DEADLINE_EXCEEDED", DEPENDENCY, RETRYABLE, "end-to-end decision deadline exceeded", "Retry with a new deadline; investigate slow dependency."),
    ReasonCode("G14_CANCELLED", CALLER, RETRYABLE, "caller cancelled the decision", "None."),
    ReasonCode("G14_OVERLOADED", DEPENDENCY, RETRYABLE, "admission control rejected (concurrency/queue)", "Back off; scale out."),
    ReasonCode("G14_NOT_CONVERGED", POLICY, FAIL_CLOSED, "dataset has no valid convergence proof", "Wait for GAP-05 convergence."),
    ReasonCode("G14_COMPUTE_INCOMPATIBLE", POLICY, FAIL_CLOSED, "compute site lacks arch/runtime/capacity", "Check SCH-01 placement data."),
    ReasonCode("G14_QUOTA_EXCEEDED", POLICY, FAIL_CLOSED, "destination quota/reservation insufficient", "Request quota or choose another site."),
    ReasonCode("G14_HANDOFF_REJECTED", DEPENDENCY, OPERATOR, "PLN-06 refused the handoff", "Inspect PLN-06 response; decision remains unexecuted."),
    ReasonCode("G14_HANDOFF_DUPLICATE", CALLER, DEGRADABLE, "idempotent duplicate handoff; original returned", "None."),
    ReasonCode("G14_NOT_EXECUTABLE", SECURITY, FAIL_CLOSED, "simulation/shadow artifact submitted for execution", "Simulations never execute; run a real decision."),
    # internal / config / audit
    ReasonCode("G14_AUDIT_UNAVAILABLE", INTERNAL, FAIL_CLOSED, "audit sink write failed; decision withheld", "Restore audit storage; no decision is emitted without audit."),
    ReasonCode("G14_AUDIT_CHAIN_BROKEN", SECURITY, OPERATOR, "audit chain verification failed", "Preserve evidence; start incident runbook RB-02."),
    ReasonCode("G14_CONFIG_INVALID", CALLER, FAIL_CLOSED, "configuration failed schema/semantic validation", "Fix config; previous revision stays active."),
    ReasonCode("G14_CONFIG_FORBIDDEN_IN_PRODUCTION", SECURITY, FAIL_CLOSED, "dev/test convenience enabled in production mode", "Remove the flag."),
    ReasonCode("G14_NOT_READY", INTERNAL, RETRYABLE, "service not ready (config/deps)", "See /readyz details."),
    ReasonCode("G14_INTERNAL", INTERNAL, OPERATOR, "unexpected internal fault", "Collect trace id; file incident."),
    # pk_core compat
    ReasonCode("G14_PKCORE_MISSING", DEPENDENCY, FAIL_CLOSED, "pk_core runtime not importable", "Install the certified pk_core build."),
    ReasonCode("G14_PKCORE_UNTRUSTED_PATH", SECURITY, FAIL_CLOSED, "pk_core imported from user-global/unapproved path", "Use the locked environment."),
    ReasonCode("G14_PKCORE_INCOMPATIBLE", DEPENDENCY, FAIL_CLOSED, "pk_core version/API/schema outside certified range", "Install a certified version."),
    ReasonCode("G14_PKCORE_DIGEST_MISMATCH", SECURITY, FAIL_CLOSED, "pk_core build digest differs from pin", "Reinstall from the locked artifact."),
    ReasonCode("G14_GATE_PARTIAL", INTERNAL, FAIL_CLOSED, "conformance gate did not attempt every check", "Never report partial as PASS; fix skips."),
    ReasonCode("G14_DRIFT_DETECTED", INTERNAL, OPERATOR, "cost model predictions drifted from observations", "Recalibrate; shadow the new model first."),
]

REGISTRY: Mapping[str, ReasonCode] = MappingProxyType({c.code: c for c in _CODES})
assert len(REGISTRY) == len(_CODES), "duplicate reason code"


class G14Error(GravityDecisionError):
    """Service-layer error carrying a registered reason code."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None):
        if code not in REGISTRY:
            raise KeyError(f"unregistered reason code {code}")
        super().__init__(message, details=details)
        self.code = code

    @property
    def reason(self) -> ReasonCode:
        return REGISTRY[self.code]

    def as_dict(self) -> dict[str, Any]:
        d = super().as_dict()
        d.update(category=self.reason.category, disposition=self.reason.disposition)
        return d


def describe(code: str) -> dict[str, str]:
    r = REGISTRY[code]
    return {"code": r.code, "category": r.category, "disposition": r.disposition,
            "summary": r.summary, "operator_action": r.operator_action}
