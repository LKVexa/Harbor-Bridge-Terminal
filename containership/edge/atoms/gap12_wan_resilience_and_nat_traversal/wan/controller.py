"""GAP-12 path controller: the v4.2.0 ``Path`` state machine wired to real
adapters and to every policy input (the integration the v4.2.0 README left to
"Day 0").

Order of gates on ``connect(peer)`` — each yields a stable reason code:
  1. quarantine (peer)                         -> POLICY_QUARANTINED
  2. rate limiter (source/peer/tenant/global)  -> BUDGET_RATE_LIMITED
  3. circuit breaker (per site)                -> BUDGET_BREAKER_OPEN
  4. egress policy for every endpoint an adapter will contact -> POLICY_EGRESS_DENIED
  5. for each strategy in configured cost order, skipping mechanisms disabled
     by config or the kill switch (POLICY_MECHANISM_DISABLED): run the adapter
     under ``AttemptRunner`` with a hard deadline
  6. identity: a path is reported *trusted* only if the TrustGate admits the
     peer; with ``require_attestation`` an untrusted success is refused
     (POLICY_UNTRUSTED_PEER) — a failed mechanism can never fall through to a
     path that bypasses identity, egress or encryption policy.

Everything is observable: metrics, a JSON event per decision, a trace span per
attempt, and ``explain(peer)`` for operators.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..path import STRATEGIES, Partitioned, Path
from . import obs, reasons
from .quality import AttemptRunner
from .security import CircuitBreaker, EgressPolicy, RateLimiter, RetryBudget, TrustGate
from .state import PathStore, Quarantine


@dataclass
class Adapter:
    """Base adapter: ``attempt(cancel) -> bool``; ``endpoints()`` for the egress gate; ``cleanup()``."""
    name: str

    def endpoints(self) -> list[tuple[str, int]]:
        return []

    def attempt(self, cancel) -> bool:          # pragma: no cover - interface
        raise NotImplementedError

    def cleanup(self) -> None:
        pass

    def evidence(self) -> bytes:
        return b""


@dataclass
class Controller:
    config: dict
    trust: TrustGate
    egress: EgressPolicy
    limiter: RateLimiter
    killswitch: object = None
    store: PathStore = field(default_factory=PathStore)
    runner: AttemptRunner = field(default_factory=AttemptRunner)
    metrics: obs.Metrics = field(default_factory=obs.Metrics)
    events: obs.EventLog = field(default_factory=obs.EventLog)
    tracer: obs.Tracer = field(default_factory=obs.Tracer)
    quarantine: Quarantine = field(default_factory=Quarantine)
    breakers: dict = field(default_factory=dict)
    budget: RetryBudget = field(default_factory=RetryBudget)
    decisions: dict = field(default_factory=dict)

    def _mech_on(self, m: str) -> bool:
        if not self.config.get("mechanisms", {}).get(m, False):
            return False
        return self.killswitch is None or self.killswitch.enabled(m)

    def connect(self, peer: str, adapters: dict[str, Adapter], *, site: str = "default", source: str = "local",
                tenant: str = "default") -> dict:
        root = self.tracer.start("request")
        trail: list[dict] = []
        self.decisions[peer] = trail

        def finish(ok: bool, reason: str, strategy: str | None = None, trusted: bool = False) -> dict:
            reasons.check(reason)
            self.tracer.end(root, outcome=reason)
            out = {"peer": peer, "ok": ok, "reason": reason, "strategy": strategy, "trusted": trusted,
                   "trail": trail, "state": self.store.snapshot(peer)}
            if ok:
                self.events.emit("G12-E001", reason, peer_token=peer, strategy=strategy)
            elif reasons.reason_class(reason) in ("policy", "auth"):
                self.events.emit("G12-E004", reason, peer_token=peer)
                self.metrics.inc("g12_policy_rejections_total", {"reason": reason})
            return out

        now = self.store.clock.monotonic()
        if self.quarantine.blocked(peer, now):
            return finish(False, "POLICY_QUARANTINED")
        ok, level = self.limiter.allow({"source": source, "peer": peer, "tenant": tenant, "global": "all"})
        if not ok:
            return finish(False, "BUDGET_RATE_LIMITED")
        br = self.breakers.setdefault(site, CircuitBreaker(clock=self.store.clock.monotonic))
        admitted, why = br.admit()
        if not admitted:
            return finish(False, why)
        self.budget.first_attempt()

        order = [s for s in self.config.get("strategies", list(STRATEGIES)) if s in adapters]
        usable: dict[str, Adapter] = {}
        for s in order:
            if not self._mech_on(s):
                trail.append({"strategy": s, "outcome": "skipped", "reason": "POLICY_MECHANISM_DISABLED"})
                continue
            denied = [e for e in adapters[s].endpoints() if self.egress.check(e[0], e[1]) != "OK"]
            if denied:
                trail.append({"strategy": s, "outcome": "skipped", "reason": "POLICY_EGRESS_DENIED"})
                continue
            usable[s] = adapters[s]
        if not usable:
            br.record(False)
            reason = trail[-1]["reason"] if trail else "POLICY_MECHANISM_DISABLED"
            return finish(False, reason)

        timeouts = self.config.get("attempt_timeout_s", 3.0)

        def prober(strategy: str) -> bool:
            a = usable.get(strategy)
            if a is None:
                return False
            sp = self.tracer.start("attempt", parent=root)
            t0 = time.monotonic()
            good, rec = self.runner.run(strategy, a.attempt, timeout=timeouts, cleanup=a.cleanup)
            reason = rec.outcome if rec.outcome in reasons.REASONS else ("OK" if good else "NET_UNREACHABLE")
            if good and self.config.get("require_attestation", True):
                admitted_, why_ = self.trust.admit(peer, a.evidence())
                if not admitted_:
                    good, reason = False, why_ if why_ != "DEP_UNAVAILABLE" else "POLICY_UNTRUSTED_PEER"
            trail.append({"strategy": strategy, "outcome": "success" if good else "failure", "reason": reason,
                          "elapsed": round(time.monotonic() - t0, 4), "cleanup_finished": rec.cleanup_finished})
            self.metrics.inc("g12_attempts_total", {"strategy": strategy, "outcome": "ok" if good else reasons.reason_class(reason)})
            if good:
                self.metrics.observe("g12_establish_seconds", {"strategy": strategy}, time.monotonic() - t0)
            else:
                self.events.emit("G12-E002", reason, peer_token=peer, strategy=strategy)
            self.tracer.end(sp, strategy=strategy, outcome=reason)
            return good

        def run(path: Path, now: float):
            return path.connect(prober, now)

        result, _ = self.store.transition(peer, run)
        if isinstance(result, Partitioned):
            if any(t["outcome"] != "skipped" for t in trail):
                br.record(False)
                self.metrics.inc("g12_partitions_total")
            self.events.emit("G12-E003", "NET_UNREACHABLE", peer_token=peer)
            attempted = [t for t in trail if t["outcome"] != "skipped"]
            if not attempted:
                return finish(False, "BUDGET_BACKOFF_ACTIVE")
            last = next((t["reason"] for t in reversed(trail) if t["outcome"] == "failure"), "NET_UNREACHABLE")
            return finish(False, last)
        br.record(True)
        strategy = result["strategy"]
        return finish(True, "OK", strategy, trusted=self.trust.is_trusted(peer))

    def explain(self, peer: str) -> dict:
        return obs.explain(self.store.snapshot(peer), self.decisions.get(peer, []))
