"""Stable reason codes (G12-G079) shared by every GAP-12 module.

Codes are versioned (REASONS_VERSION) and never reused.  Each code belongs to
exactly one class so operators can tell network failure from dependency
failure, policy rejection, authentication failure, budget exhaustion, software
defect, cancellation and operator action (G75-07).
"""
from __future__ import annotations

REASONS_VERSION = "G12-REASONS/1"

CLASSES = ("network", "dependency", "policy", "auth", "budget", "defect", "cancelled", "operator", "ok")

REASONS: dict[str, tuple[str, str]] = {
    # code: (class, description)
    "OK": ("ok", "operation succeeded"),
    "NET_TIMEOUT": ("network", "no response before the deadline"),
    "NET_UNREACHABLE": ("network", "destination or route unreachable"),
    "NET_REFUSED": ("network", "peer actively refused the connection"),
    "NET_UDP_BLOCKED": ("network", "UDP produced no response from any server while TCP works or was not tried"),
    "NET_MAPPING_CHANGED": ("network", "NAT mapping changed during the operation"),
    "NET_MTU_BLACKHOLE": ("network", "large probes vanish while small ones succeed"),
    "NET_FILTERED": ("network", "NAT/firewall filtering dropped the traffic"),
    "DNS_NXDOMAIN": ("dependency", "name does not exist"),
    "DNS_SERVFAIL": ("dependency", "resolver reported SERVFAIL"),
    "DNS_TIMEOUT": ("dependency", "no resolver answered before the deadline"),
    "DNS_MISMATCH": ("auth", "response did not match the outstanding query (possible poisoning)"),
    "DNS_CONFIG": ("defect", "local resolver configuration unusable"),
    "DEP_UNAVAILABLE": ("dependency", "a required dependency is unavailable"),
    "DEP_MALFORMED": ("dependency", "a dependency returned a malformed response"),
    "DEP_INCONSISTENT": ("dependency", "independent servers disagreed"),
    "POLICY_EGRESS_DENIED": ("policy", "egress policy forbids this destination"),
    "POLICY_MECHANISM_DISABLED": ("policy", "traversal mechanism disabled by policy or kill switch"),
    "POLICY_QUARANTINED": ("policy", "backend or peer is quarantined"),
    "POLICY_UNTRUSTED_PEER": ("policy", "peer identity not attested or attestation stale"),
    "POLICY_CONFIG_REJECTED": ("policy", "configuration failed validation"),
    "AUTH_FAILED": ("auth", "authentication failed"),
    "AUTH_INTEGRITY": ("auth", "message integrity check failed"),
    "AUTH_REPLAY": ("auth", "replayed or out-of-window message"),
    "AUTH_TLS_CERT": ("auth", "TLS certificate/identity verification failed"),
    "AUTH_STALE_NONCE": ("auth", "server demanded a fresh nonce"),
    "BUDGET_RATE_LIMITED": ("budget", "rate limiter refused the attempt"),
    "BUDGET_QUOTA_EXHAUSTED": ("budget", "relay quota exhausted"),
    "BUDGET_BREAKER_OPEN": ("budget", "circuit breaker open"),
    "BUDGET_RETRY_EXHAUSTED": ("budget", "retry budget exhausted"),
    "BUDGET_BACKOFF_ACTIVE": ("budget", "peer is inside its jittered retry window; no attempt was made"),
    "DEFECT_EXCEPTION": ("defect", "adapter raised an unexpected exception"),
    "DEFECT_PROTOCOL": ("defect", "local protocol state violated"),
    "CANCELLED_DEADLINE": ("cancelled", "attempt cancelled at its hard deadline"),
    "CANCELLED_SHUTDOWN": ("cancelled", "attempt cancelled by shutdown"),
    "OPERATOR_DISABLED": ("operator", "operator disabled the mechanism"),
    "OPERATOR_OVERRIDE": ("operator", "operator override applied"),
    "UNSUPPORTED": ("defect", "sub-case explicitly unsupported by this build"),
}


def reason_class(code: str) -> str:
    try:
        return REASONS[code][0]
    except KeyError as exc:
        raise KeyError(f"unregistered reason code {code!r}") from exc


def check(code: str) -> str:
    reason_class(code)
    return code
