"""Operator-facing facade: health, readiness, status, explain, lineage, recurring review (MC-056, MC-057,
MC-063, MC-064, MC-074).

``Inv28Service`` wires the registry, policy, selector and observability together and exposes the
operator surface as plain functions returning JSON-serialisable dicts - a host process can mount
them on HTTP, gRPC or a CLI (``python -m inv28_unikernel_implementations.cli``).
"""
from __future__ import annotations

import datetime as dt
import platform
import sys

from .errors import Inv28Error, Reason
from .model import fmt_utc, sha256_hex
from .observability import AuditLedger, Metrics, StructuredLogger, TelemetryPolicy

VERSION_FILE = __import__("pathlib").Path(__file__).with_name("VERSION")


class Inv28Service:
    def __init__(self, *, registry, selector, clock=None, metrics=None, logger=None, audit=None,
                 telemetry: TelemetryPolicy | None = None):
        self.registry = registry
        self.selector = selector
        self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self.metrics = metrics or selector.metrics or Metrics()
        self.logger = logger or selector.logger or StructuredLogger()
        self.audit = audit or selector.audit or AuditLedger()
        self.telemetry = telemetry or TelemetryPolicy()

    # -- MC-056 ----------------------------------------------------------------------------------
    def health(self) -> dict:
        """Liveness: the process can answer and its in-memory state is internally consistent."""
        problems = self.audit.verify()
        return {"status": "ok" if not problems else "degraded", "audit_chain": "intact" if not problems else problems[:5]}

    def readiness(self) -> dict:
        """Readiness: can this instance make a *production* decision right now?  Fail-closed reasons listed."""
        now = self.clock()
        reasons = []
        rule = self.selector.policy.environments.get("production")
        if not self.registry.entries:
            reasons.append("registry empty")
        if rule is not None:
            if rule.require_certification and (self.selector.certifications is None or not len(self.selector.certifications)):
                reasons.append("no GAP-15 certifications loaded")
            if rule.require_advisory_feed and (self.selector.advisories is None or self.selector.advisories.stale(now)):
                reasons.append("advisory feed missing or stale")
        if self.audit.verify():
            reasons.append("audit chain broken")
        return {"ready": not reasons, "reasons": reasons, "checked_at": fmt_utc(now)}

    # -- MC-057 ----------------------------------------------------------------------------------
    def status(self) -> dict:
        now = self.clock()
        pol = self.selector.policy
        stale = self.stale_reviews(now)
        self.metrics.set("inv28_stale_reviews", len(stale))
        self.metrics.set("inv28_registry_revision", self.registry.revision)
        by: dict[tuple, int] = {}
        for r in self.registry.entries:
            by[(r.maturity, r.lifecycle)] = by.get((r.maturity, r.lifecycle), 0) + 1
        for (m, lc), n in by.items():
            self.metrics.set("inv28_toolchains_registered", n, maturity=m, lifecycle=lc)
        return {
            "component": "INV-28", "version": VERSION_FILE.read_text().strip(),
            "python": sys.version.split()[0], "platform": platform.platform(terse=True),
            "registry": {"revision": self.registry.revision, "digest": self.registry.digest,
                         "entries": len(self.registry.entries)},
            "policy": {"id": pol.policy_id, "revision": pol.revision, "digest": pol.digest,
                       "environments": sorted(pol.environments), "waivers": len(pol.waivers)},
            "dependencies": {
                "gap15_certifications": None if self.selector.certifications is None else len(self.selector.certifications),
                "advisory_feed_stale": None if self.selector.advisories is None else self.selector.advisories.stale(now),
                "gap08_pending_announcements": len(self.selector.rollout.pending_announcements) if self.selector.rollout else None,
            },
            "stale_reviews": stale, "audit_head": self.audit.head, "readiness": self.readiness(),
        }

    # -- MC-074 recurring review -----------------------------------------------------------------
    def stale_reviews(self, now: dt.datetime) -> list[str]:
        out = []
        for r in self.registry.entries:
            if r.lifecycle in ("retired",):
                continue
            if r.review is None or r.review.stale(now):
                out.append(r.ref)
        return sorted(out)

    def reviews_due(self, now: dt.datetime, within: dt.timedelta = dt.timedelta(days=14)) -> list[dict]:
        due = []
        for r in self.registry.entries:
            if r.lifecycle == "retired":
                continue
            exp = r.review.expires_at() if r.review else None
            if exp is None or exp - now <= within:
                due.append({"toolchain": r.ref, "expires_at": fmt_utc(exp) if exp else None,
                            "owner": r.owner, "overdue": exp is None or exp < now})
        return sorted(due, key=lambda d: (d["expires_at"] or "", d["toolchain"]))

    # -- MC-063 ----------------------------------------------------------------------------------
    def explain(self, decision_id: str) -> str:
        from .explain import render
        hits = [e for e in self.audit.entries() if e["payload"].get("decision_id") == decision_id]
        if not hits:
            raise Inv28Error(Reason.REGISTRY_UNKNOWN, f"no recorded decision {decision_id}")
        return render(hits[-1], self.selector.policy)

    # -- MC-064 ----------------------------------------------------------------------------------
    def lineage(self, decision_id: str, *, release_manifest_sha256: str = "") -> dict:
        hits = [e for e in self.audit.entries() if e["payload"].get("decision_id") == decision_id]
        if not hits:
            raise Inv28Error(Reason.REGISTRY_UNKNOWN, f"no recorded decision {decision_id}")
        e = hits[-1]
        p = e["payload"]
        nodes = [
            {"kind": "component_release", "id": f"INV-28@{VERSION_FILE.read_text().strip()}",
             "manifest_sha256": release_manifest_sha256},
            {"kind": "policy", "id": p.get("policy_digest")},
            {"kind": "registry_revision", "id": p.get("registry_revision")},
            {"kind": "decision", "id": decision_id, "ledger_entry": e["entry_hash"]},
        ]
        if p.get("toolchain"):
            nodes += [{"kind": "toolchain", "id": p["toolchain"], "record_digest": p.get("record_digest")},
                      {"kind": "gap15_certificate", "id": p.get("certification_id")}]
        edges = [[nodes[i]["kind"], nodes[i + 1]["kind"]] for i in range(len(nodes) - 1)]
        return {"schema": "PK_LINEAGE/1", "nodes": nodes, "edges": edges, "digest": sha256_hex(nodes)}
