"""Authenticated health-gate adapter (component 4; GAP-09 contract).

A production gate is never satisfied by a caller-supplied boolean.  The adapter
accepts only a signed ``PK_HEALTH_EVIDENCE/1`` envelope from an allow-listed
observability source and checks, in order:

1. signature from an active key belonging to an allow-listed source;
2. binding to this rollout, wave/retry cohort and gate class (no cross-rollout reuse);
3. freshness (``observed_at`` no older than ``max_age_s``, not in the future);
4. observation window starts after the wave settled (evidence cannot predate the change);
5. minimum sample coverage of the cohort;
6. internal consistency (verdict agrees with sample counts);
7. anti-replay (evidence id + nonce never accepted twice).

Any failure raises ``EvidenceRejected`` — which the controller treats as *gate
not passed* (hold), never as healthy.  An unreachable source raises
``DependencyUnavailable`` (fail closed).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from .common import Clock, KeyRing, SystemClock, digest_of, verify_envelope
from .errors import EvidenceRejected

HEALTH_SCHEMA = "PK_HEALTH_EVIDENCE/1"


@dataclass(frozen=True)
class GatePolicy:
    gate_class: str = "wave"
    max_age_s: float = 300.0
    settle_s: float = 60.0
    min_coverage: float = 0.9           # fraction of touched nodes that must be sampled
    min_healthy_ratio: float = 0.99     # healthy/sampled needed for a "healthy" verdict
    future_skew_s: float = 5.0


@dataclass(frozen=True)
class GateDecision:
    healthy: bool
    evidence_id: str
    evidence_digest: str
    source: str
    coverage: float
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class HealthGateAdapter:
    keyring: KeyRing
    source_keys: dict[str, set[str]]    # source identity -> allowed key ids
    clock: Clock = field(default_factory=SystemClock)
    _seen: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def evaluate(self, envelope: Mapping[str, Any], *, rollout_id: str, cohort: str, nodes: list[str],
                 applied_at: float, policy: GatePolicy = GatePolicy()) -> GateDecision:
        body = verify_envelope(self.keyring, envelope)
        if body is None:
            raise EvidenceRejected("health evidence signature invalid or key inactive", resource=rollout_id)
        if body.get("schema") != HEALTH_SCHEMA:
            raise EvidenceRejected(f"unsupported health schema {body.get('schema')!r}", resource=rollout_id)
        source = body.get("source")
        if envelope.get("key_id") not in self.source_keys.get(source, set()):
            raise EvidenceRejected(f"key {envelope.get('key_id')} is not authorised for source {source}",
                                   resource=rollout_id)
        if body.get("rollout_id") != rollout_id or body.get("cohort") != cohort \
                or body.get("gate_class") != policy.gate_class:
            raise EvidenceRejected("evidence is bound to a different rollout, cohort or gate class",
                                   resource=rollout_id)
        now = self.clock.now()
        observed = body.get("observed_at")
        if not isinstance(observed, (int, float)) or observed > now + policy.future_skew_s:
            raise EvidenceRejected("evidence timestamp missing or in the future", resource=rollout_id)
        if now - observed > policy.max_age_s:
            raise EvidenceRejected(f"evidence is stale ({now - observed:.0f}s old)", resource=rollout_id)
        ws, we = body.get("window_start"), body.get("window_end")
        if not all(isinstance(x, (int, float)) for x in (ws, we)) or not (ws <= we <= observed + policy.future_skew_s):
            raise EvidenceRejected("observation window malformed", resource=rollout_id)
        if ws < applied_at + policy.settle_s:
            raise EvidenceRejected("observation window predates the settled change", resource=rollout_id)
        sampled = body.get("sampled_nodes")
        healthy_nodes = body.get("healthy_nodes")
        if not isinstance(sampled, list) or not isinstance(healthy_nodes, list):
            raise EvidenceRejected("evidence lacks per-node samples", resource=rollout_id)
        cohort_set = set(nodes)
        sampled_set = set(sampled) & cohort_set
        if set(sampled) - cohort_set:
            raise EvidenceRejected("evidence samples nodes outside the cohort", resource=rollout_id)
        if not set(healthy_nodes) <= set(sampled):
            raise EvidenceRejected("healthy set is not a subset of sampled set (contradictory)", resource=rollout_id)
        coverage = (len(sampled_set) / len(cohort_set)) if cohort_set else 1.0
        if coverage < policy.min_coverage:
            raise EvidenceRejected(f"coverage {coverage:.2%} below {policy.min_coverage:.0%}", resource=rollout_id)
        ratio = (len(healthy_nodes) / len(sampled_set)) if sampled_set else 1.0
        computed = ratio >= policy.min_healthy_ratio
        verdict = body.get("verdict")
        if verdict not in ("healthy", "unhealthy"):
            raise EvidenceRejected("verdict must be 'healthy' or 'unhealthy'", resource=rollout_id)
        if verdict == "healthy" and not computed:
            raise EvidenceRejected("verdict contradicts sample counts", resource=rollout_id)
        replay_key = f"{source}:{body.get('evidence_id')}:{body.get('nonce')}"
        with self._lock:
            if replay_key in self._seen:
                raise EvidenceRejected("health evidence replayed", resource=rollout_id)
            self._seen.add(replay_key)
        healthy = verdict == "healthy" and computed
        return GateDecision(healthy, str(body.get("evidence_id")), digest_of(dict(envelope)), str(source),
                            coverage, f"{len(healthy_nodes)}/{len(sampled_set)} healthy; coverage {coverage:.0%}")
