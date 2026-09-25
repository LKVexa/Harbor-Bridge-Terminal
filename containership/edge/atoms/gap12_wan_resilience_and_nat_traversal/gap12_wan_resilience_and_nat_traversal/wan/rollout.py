"""Staged rollout / rollback (G12-I107) and the emergency kill switch
(G12-I108).

``KillSwitch`` controls are signed (HMAC-SHA256 under an operator key held in
the secret provider), scoped (global / environment / site / mechanism),
monotonically versioned (a replayed or older control is refused), expiring,
reversible, and audited.  If the control plane is unreachable the node keeps
the LAST VERIFIED control set; a node that has never received one uses the
safe default in which the risky mechanisms (upnp, natpmp, pcp, quic) are
disabled and the core path (direct, hole-punch, relay) stays enabled.

``Rollout`` is a canary state machine: stages (1 %, 10 %, 50 %, 100 %), each
gated on health criteria for a soak period; any criterion breach triggers an
automatic rollback; an operator can pause/resume/rollback manually; a
compatibility check against the previous version runs before stage 1.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field

RISKY = ("upnp", "natpmp", "pcp", "quic")
SAFE_DEFAULT = {"direct": True, "hole-punch": True, "relay": True, "tcp": True, "tls": True,
                "upnp": False, "natpmp": False, "pcp": False, "quic": False}


def sign_control(key: bytes, control: dict) -> dict:
    body = json.dumps(control, sort_keys=True, separators=(",", ":"))
    return {"control": control, "sig": hmac.new(key, body.encode(), hashlib.sha256).hexdigest()}


class KillSwitch:
    def __init__(self, key: bytes, *, node_scope: dict, audit=None, clock=time.time):
        self.key, self.scope, self.audit, self.clock = key, node_scope, audit, clock
        self.version = 0
        self.disabled: dict[str, dict] = {}       # mechanism -> control
        self.last_verified_at: float | None = None
        self.explicit: set[str] = set()

    def _applies(self, c: dict) -> bool:
        target = c.get("scope", {})
        return all(self.scope.get(k) == v for k, v in target.items() if k != "global")

    def apply(self, signed: dict, *, actor: str) -> str:
        c = signed.get("control", {})
        body = json.dumps(c, sort_keys=True, separators=(",", ":"))
        if not hmac.compare_digest(hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest(), signed.get("sig", "")):
            self._audit("killswitch_rejected", "AUTH_INTEGRITY", actor, c)
            return "AUTH_INTEGRITY"
        if c.get("version", 0) <= self.version:
            self._audit("killswitch_rejected", "AUTH_REPLAY", actor, c)
            return "AUTH_REPLAY"
        if c.get("expires", 0) <= self.clock():
            return "AUTH_REPLAY"
        self.version = c["version"]
        self.last_verified_at = self.clock()
        if not self._applies(c):
            self._audit("killswitch_out_of_scope", "OK", actor, c)
            return "OK"
        for m in c.get("disable", []):
            self.disabled[m] = c
            self.explicit.discard(m)
        for m in c.get("enable", []):
            self.disabled.pop(m, None)
            if m in RISKY:
                self.explicit.add(m)
        self._audit("killswitch_applied", "OPERATOR_DISABLED" if c.get("disable") else "OPERATOR_OVERRIDE", actor, c)
        return "OK"

    def enabled(self, mechanism: str) -> bool:
        now = self.clock()
        for m, c in list(self.disabled.items()):
            if c["expires"] <= now:
                del self.disabled[m]              # disable controls expire (reversible by time too)
        if mechanism in self.disabled:
            return False
        if mechanism in RISKY:
            return mechanism in self.explicit     # risky mechanisms need an explicit signed enable
        return SAFE_DEFAULT.get(mechanism, False)

    def _audit(self, event, reason, actor, c):
        if self.audit is not None:
            self.audit.append(event, reason=reason, actor=actor, subject=",".join(c.get("disable", []) + c.get("enable", [])),
                              detail={"version": c.get("version"), "scope": c.get("scope")})


STAGES = (0.01, 0.10, 0.50, 1.00)


@dataclass
class Criteria:
    max_error_rate: float = 0.01
    max_p95_establish_s: float = 3.0
    max_relay_ratio: float = 0.5
    min_samples: int = 50


@dataclass
class Rollout:
    version: str
    previous: str
    soak_s: float = 600.0
    criteria: Criteria = field(default_factory=Criteria)
    stage: int = -1
    state: str = "pending"          # pending | running | paused | rolled_back | complete | blocked
    stage_started: float | None = None
    log: list[dict] = field(default_factory=list)

    def compatibility(self, check) -> bool:
        ok, detail = check(self.previous, self.version)
        self.log.append({"event": "compat_check", "ok": ok, "detail": detail})
        if not ok:
            self.state = "blocked"
        return ok

    def start(self, now: float) -> None:
        if self.state not in ("pending",):
            raise RuntimeError(f"cannot start from {self.state}")
        self.stage, self.state, self.stage_started = 0, "running", now
        self.log.append({"event": "stage", "fraction": STAGES[0], "t": now})

    def fraction(self) -> float:
        return 0.0 if self.stage < 0 or self.state == "rolled_back" else STAGES[self.stage]

    def evaluate(self, health: dict, now: float) -> str:
        if self.state != "running":
            return self.state
        c = self.criteria
        if health.get("samples", 0) >= c.min_samples:
            breach = [k for k, bad in (("error_rate", health["error_rate"] > c.max_error_rate),
                                       ("p95_establish_s", health["p95_establish_s"] > c.max_p95_establish_s),
                                       ("relay_ratio", health["relay_ratio"] > c.max_relay_ratio)) if bad]
            if breach:
                self.rollback(now, reason="criteria breach: " + ",".join(breach), actor="automation")
                return self.state
        else:
            return self.state                                  # not enough evidence: hold, never promote
        if now - self.stage_started >= self.soak_s:
            if self.stage == len(STAGES) - 1:
                self.state = "complete"
            else:
                self.stage += 1
                self.stage_started = now
                self.log.append({"event": "stage", "fraction": STAGES[self.stage], "t": now})
        return self.state

    def pause(self, actor: str) -> None:
        if self.state == "running":
            self.state = "paused"
            self.log.append({"event": "pause", "actor": actor})

    def resume(self, actor: str, now: float) -> None:
        if self.state == "paused":
            self.state, self.stage_started = "running", now
            self.log.append({"event": "resume", "actor": actor})

    def rollback(self, now: float, *, reason: str, actor: str) -> None:
        self.state = "rolled_back"
        self.log.append({"event": "rollback", "to": self.previous, "reason": reason, "actor": actor, "t": now})
