"""Feature-subset certification model (component 19).

Features are hierarchical (``wasi:http/outgoing``); passing a child never
implies its parent or siblings (MC-19-01). A subset decision covers exactly
the required set: ``compatible`` only if every required feature (and each of
its declared prerequisites) has fresh passing evidence and none is failed,
revoked or expired (MC-19-03, MC-19-06, MC-19-07). Aggregation across records
is conservative: any unexpired failure beats a pass of equal or lower
authority; newer higher-authority passes still route to conflict review
rather than silently winning (MC-19-04).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .canonical import digest

PASSED, FAILED, NOT_TESTED, REVOKED, EXPIRED = "passed", "failed", "not-tested", "revoked", "expired"


@dataclass(frozen=True)
class FeatureEvidence:
    feature: str
    result: str  # passed | failed
    evidence_id: str
    tested_at: int
    authority: int = 1


@dataclass
class FeatureGraph:
    prerequisites: dict = field(default_factory=dict)  # feature -> set(prereq)
    conflicts: dict = field(default_factory=dict)  # feature -> set(conflicting)

    def closure(self, features: set) -> set:
        out, stack = set(), list(features)
        while stack:
            f = stack.pop()
            if f in out:
                continue
            out.add(f)
            stack.extend(self.prerequisites.get(f, ()))
        return out


def aggregate(records: list, *, now: int, ttl_s: int, revoked_evidence: frozenset = frozenset()) -> dict:
    """Per-feature status with evidence ids (MC-19-05)."""
    by_feature: dict = {}
    for rec in sorted(records, key=lambda r: (r.feature, r.tested_at, r.evidence_id)):
        by_feature.setdefault(rec.feature, []).append(rec)
    out = {}
    for feat, recs in by_feature.items():
        live = [r for r in recs if r.evidence_id not in revoked_evidence and r.tested_at <= now]
        if not live:
            out[feat] = {"status": REVOKED if recs else NOT_TESTED, "evidence": [r.evidence_id for r in recs]}
            continue
        failures = [r for r in live if r.result == FAILED]
        passes = [r for r in live if r.result == PASSED and now - r.tested_at <= ttl_s]
        if failures:
            top_fail = max(r.authority for r in failures)
            newer_stronger = [p for p in passes if p.authority > top_fail and p.tested_at > max(f.tested_at for f in failures)]
            status = "conflict" if newer_stronger else FAILED
        elif passes:
            status = PASSED
        else:
            status = EXPIRED
        out[feat] = {"status": status, "evidence": [r.evidence_id for r in live]}
    return out


def subset_decision(required: set, graph: FeatureGraph, status: dict, *, forbidden: set = frozenset()) -> dict:
    needed = graph.closure(set(required))
    per = {}
    for f in sorted(needed):
        per[f] = status.get(f, {"status": NOT_TESTED, "evidence": []})
    blocked = sorted(f for f, s in per.items() if s["status"] != PASSED)
    forbidden_hit = sorted(f for f in forbidden if status.get(f, {}).get("status") == PASSED and f in required)
    conflicts = sorted(f for f in required for g in graph.conflicts.get(f, ()) if g in required)
    compatible = not blocked and not forbidden_hit and not conflicts
    return {
        "scope": "partial" if needed else "empty",
        "coverage": "feature-subset",  # never whole-runtime (MC-19-03, MC-19-10)
        "required": sorted(required),
        "required_closure": sorted(needed),
        "required_set_digest": digest(sorted(required)),  # cache key component (MC-19-08)
        "compatible": compatible,
        "features": per,
        "blocked": blocked,
        "forbidden_present": forbidden_hit,
        "conflicts": conflicts,
    }
