"""Execution semantics for INV-70.

C015  execution lifecycle state machine (legal transitions only; terminal states final)
C019  constraint-conflict precedence policy (deterministic, security first)
C027  mixed-version protocol negotiation for PK_FASTBOX_RUN / RESULT / HOSTCALL
C093  supported-version window and enforcement
"""
from __future__ import annotations

import threading
from enum import Enum

# ------------------------------------------------------------------ C015
class State(str, Enum):
    RECEIVED = "received"
    AUTHENTICATED = "authenticated"
    ADMITTED = "admitted"
    VALIDATED = "validated"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    TRAPPED = "trapped"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"          # infrastructure failure (worker crash, backend unavailable)


TERMINAL = frozenset({State.SUCCEEDED, State.TRAPPED, State.REJECTED, State.CANCELLED,
                      State.TIMED_OUT, State.FAILED})
_ABORTS = {State.REJECTED, State.CANCELLED, State.TIMED_OUT, State.FAILED}
TRANSITIONS = {
    State.RECEIVED: {State.AUTHENTICATED} | _ABORTS,
    State.AUTHENTICATED: {State.ADMITTED} | _ABORTS,
    State.ADMITTED: {State.VALIDATED} | _ABORTS,
    State.VALIDATED: {State.RUNNING} | _ABORTS,
    State.RUNNING: {State.SUCCEEDED, State.TRAPPED} | _ABORTS,
}


class IllegalTransition(RuntimeError):
    pass


class Lifecycle:
    def __init__(self, run_id: str, on_transition=None):
        self.run_id = run_id
        self.state = State.RECEIVED
        self.history = [State.RECEIVED]
        self._cb = on_transition
        self._lock = threading.Lock()

    def to(self, new: State) -> None:
        with self._lock:
            if new not in TRANSITIONS.get(self.state, set()):
                raise IllegalTransition(f"{self.state.value} -> {new.value}")
            old, self.state = self.state, new
            self.history.append(new)
        if self._cb:
            self._cb(self.run_id, old, new)

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL


# ------------------------------------------------------------------ C019
# Lower rank wins.  When two constraints conflict, the higher-ranked class decides
# and the lower-ranked one is recorded as overridden - never silently dropped.
PRECEDENCE = [
    ("security", "isolation, authentication, capability denial, trust/time/audit fail-closed"),
    ("tenant_isolation", "no cross-tenant state, failover or cache sharing"),
    ("residency", "data/execution stays in allowed regions"),
    ("correctness", "deterministic termination, exact result schema"),
    ("resource_limits", "fuel, memory, wall-clock, host-call budgets"),
    ("availability", "admission, retry, failover, degraded modes"),
    ("performance", "latency/throughput optimizations, caching"),
    ("cost", "resource efficiency"),
]
RANK = {name: i for i, (name, _) in enumerate(PRECEDENCE)}


def resolve_conflict(options: list[dict]) -> dict:
    """Each option: {"action": str, "constraint": <class>}. Returns the winner plus
    the overridden list so callers can log it.  Ties -> most restrictive action
    (``deny`` beats ``allow``) and then lexical order, for determinism."""
    if not options:
        raise ValueError("no options")
    for o in options:
        if o.get("constraint") not in RANK:
            raise ValueError(f"unknown constraint class: {o.get('constraint')}")

    def key(o):
        return (RANK[o["constraint"]], 0 if o["action"] == "deny" else 1, o["action"])
    ordered = sorted(options, key=key)
    return {"winner": ordered[0], "overridden": ordered[1:]}


# ------------------------------------------------------------------ C027 / C093
PROTOCOLS = {
    "PK_FASTBOX_RUN": {1, 2},
    "PK_FASTBOX_RESULT": {1, 2},
    "PK_FASTBOX_HOSTCALL": {1},
}
DEPRECATED = {("PK_FASTBOX_RUN", 1): "2027-06-30", ("PK_FASTBOX_RESULT", 1): "2027-06-30"}

# Release -> supported peer release window (N-1 minor compatibility policy).
SUPPORTED_PEER_RELEASES = {"4.3": {"4.2", "4.3"}}
CURRENT_RELEASE = "4.3"


class VersionError(ValueError):
    pass


def negotiate(protocol: str, offered) -> int:
    """Pick the highest mutually supported version; reject unknown protocol or no overlap."""
    if protocol not in PROTOCOLS:
        raise VersionError("unknown protocol")
    try:
        offered_set = {v for v in offered if type(v) is int}
    except TypeError:
        raise VersionError("malformed version offer") from None
    common = PROTOCOLS[protocol] & offered_set
    if not common:
        raise VersionError(f"no common {protocol} version")
    return max(common)


def check_peer_release(peer_release: str) -> None:
    mm = ".".join(str(peer_release).split(".")[:2])
    if mm not in SUPPORTED_PEER_RELEASES[CURRENT_RELEASE]:
        raise VersionError(f"peer release {peer_release} unsupported")


def downgrade_result(result: dict, version: int) -> dict:
    """RESULT/2 adds run_id/status/reason_code; RESULT/1 is the original {ok|trap, fuel}."""
    if version == 2:
        return result
    out = {"fuel": result["fuel"]}
    if result["status"] == "ok":
        out["ok"] = result["value"]
    else:
        out["trap"] = result["reason"]
    return out
