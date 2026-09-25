"""Decision records and the operator ``explain`` view (MC-25; C076-C078).

Schema ``PK_APP_DECISION/1``: every automated production-impacting choice
(validation rejection, authz denial, tenancy refusal, admission rejection,
activation/rollback, degraded-mode selection) becomes one record::

    {"schema", "decision_id", "type", "outcome", "reason_codes", "dominant_constraint",
     "inputs": {"manifest_digest", "request_digest", "overlay_digests"},
     "versions": {"release", "policy", "trust", "config", "spec"},
     "lineage": {"release_id", "build_digest", "config_revision"},
     "infrastructure": {"node", "providers": [...], "graph_state": "fresh|stale|unknown"},
     "alternatives": [...], "tenant", "correlation_id", "ts"}

Only digests and stable codes are stored — never payloads — so a record can be
reproduced from the referenced inputs without leaking them. ``dominant_constraint``
applies the precedence of SPECIFICATION.md §10: security > residency > isolation >
capacity > SLO > cost. :func:`explain` renders a bounded, tenant-filtered view.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import deque
from typing import Iterable

DECISION_SCHEMA = "PK_APP_DECISION/1"
PRECEDENCE = ("security", "residency", "isolation", "capacity", "slo", "cost", "validity")

CODE_CONSTRAINT = {
    "auth": "security", "authz": "security", "secret": "security", "artifact": "security", "crypto": "security",
    "tenant": "isolation", "admission": "capacity", "deadline": "slo", "residency": "residency",
    "cost": "cost", "manifest": "validity", "schema": "validity", "name": "validity", "link": "validity",
    "trait": "validity", "section": "validity", "entry": "validity", "overlay": "validity",
    "activation": "validity", "idempotency": "validity", "version": "validity", "request": "validity",
}

CLASSIFICATION = {
    "security": "policy or identity rejection — check credentials/policy, not the manifest",
    "isolation": "tenant boundary violation — request crossed a tenant scope",
    "capacity": "load — back off and retry per retry hint",
    "slo": "deadline — dependency slowness or too-small budget",
    "validity": "invalid input — fix the manifest/overlay; retrying unchanged will fail again",
    "residency": "residency rule", "cost": "cost policy",
    "defect": "software defect — internal error; page the owner",
}


def dominant(codes: Iterable[str]) -> str | None:
    cons = {CODE_CONSTRAINT.get(c.split(".", 1)[0], "defect") for c in codes}
    if "defect" in cons:
        return "defect"
    for c in PRECEDENCE:
        if c in cons:
            return c
    return None


class DecisionLog:
    def __init__(self, *, capacity: int = 50_000, versions: dict | None = None, lineage: dict | None = None,
                 node: str = "local", clock=time.time):
        self._ring: deque[dict] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        self.versions = dict(versions or {})
        self.lineage = dict(lineage or {})
        self._node = node
        self._clock = clock

    def record(self, dtype: str, outcome: str, *, codes: Iterable[str] = (), tenant: str | None,
               correlation_id: str | None, inputs: dict | None = None, alternatives: list | None = None,
               providers: list | None = None, graph_state: str = "unknown") -> dict:
        codes = sorted(set(codes))
        body = {
            "schema": DECISION_SCHEMA, "type": dtype, "outcome": outcome, "reason_codes": codes,
            "dominant_constraint": dominant(codes) if codes else None,
            "inputs": dict(inputs or {}), "versions": dict(self.versions), "lineage": dict(self.lineage),
            "infrastructure": {"node": self._node, "providers": sorted(providers or [])[:64],
                               "graph_state": graph_state if graph_state in ("fresh", "stale", "unknown") else "unknown"},
            "alternatives": list(alternatives or [])[:16], "tenant": tenant, "correlation_id": correlation_id,
        }
        # decision_id is deterministic over the decision content (identical decisions -> identical id)
        body["decision_id"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:32]
        body["ts"] = round(self._clock(), 6)
        with self._lock:
            self._ring.append(body)
        return body

    def find(self, *, correlation_id: str | None = None, tenant: str | None = None) -> list[dict]:
        with self._lock:
            return [d for d in self._ring
                    if (correlation_id is None or d["correlation_id"] == correlation_id)
                    and (tenant is None or d["tenant"] == tenant)]


def explain(records: list[dict], *, viewer_tenant: str | None) -> dict:
    """Operator view. ``viewer_tenant=None`` is a platform operator; otherwise foreign records are hidden."""
    visible = [r for r in records if viewer_tenant is None or r.get("tenant") == viewer_tenant]
    out = []
    for r in visible[-50:]:
        cls = r["dominant_constraint"]
        entry = {
            "decision_id": r["decision_id"], "type": r["type"], "outcome": r["outcome"],
            "reason_codes": r["reason_codes"], "dominant_constraint": cls,
            "classification": CLASSIFICATION.get(cls, "accepted") if cls else "accepted",
            "inputs": r["inputs"], "versions": r["versions"], "lineage": r["lineage"],
            "infrastructure": r["infrastructure"] if viewer_tenant is None else
            {"graph_state": r["infrastructure"]["graph_state"]},   # topology hidden from tenant viewers
        }
        if r["infrastructure"]["graph_state"] != "fresh":
            entry["caveat"] = "infrastructure graph data was " + r["infrastructure"]["graph_state"]
        out.append(entry)
    return {"schema": "PK_APP_EXPLAIN/1", "decisions": out}  # no foreign-record counts (inference leak)
