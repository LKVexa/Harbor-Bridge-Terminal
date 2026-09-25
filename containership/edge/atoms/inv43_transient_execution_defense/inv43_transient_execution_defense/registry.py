"""Checklists 10, 15, 31, 32, 40: the fleet posture registry.

This is the authoritative in-process decision point that composes the other
modules.  Its security properties, each exercised by tests:

* Posture enters ONLY through :meth:`PostureRegistry.submit`, which requires
  the ``posture.write`` capability for that node AND a verified attestation
  envelope bound to that node.  There is no API that lets a caller hand the
  registry a ``MitigationState`` directly.
* Posture is fresh or it is absent: an entry older than
  ``min(collector TTL, config posture_ttl_s)`` refuses cross-tenant
  placement with ``posture_stale``.
* Split-brain / replay: every read-back carries the collector's ``epoch``
  (boot generation).  A read-back with a lower epoch than the one already
  accepted is refused (``posture_stale_epoch``); the attestation layer
  separately refuses replayed sequence numbers.
* Restart: the registry is deliberately *stateless for posture* (see
  docs/RECOVERY.md).  After a restart every node is ``posture_absent`` until
  it re-attests - the system restarts closed.  Emergency controls are NOT
  stateless: they are rebuilt from the tamper-evident audit chain via
  :meth:`restore_controls`, so a restart cannot silently lift a quarantine.
* Every decision - permit or refusal - gets a ``decision_id``, an audit
  entry, metrics, a structured log line and an explain record.
"""
from __future__ import annotations

import collections
import hashlib
import json
import threading
import time
import uuid

from . import __version__
from .attestation import KeyRegistry, verify as verify_envelope
from .authz import (CAP_CONTROL, CAP_COTENANCY_DECIDE, CAP_EXPLAIN, CAP_POSTURE_READ, CAP_POSTURE_WRITE,
                    Authorizer)
from .auditlog import AuditLog
from .collector import NodeReadback, Observation, classify
from .config import ConfigStore
from .defense import UNKNOWN, MitigationMissing, MitigationState, _require_identifier
from .policy import Policy, gap02_contradictions
from .resilience import HealthMonitor, classify_code
from .telemetry import Metrics, StructuredLogger, parse_traceparent

MAX_EXPLAIN = 10000


class _NullStream:
    def write(self, _s: str) -> int:
        return 0


def readback_from_dict(d: dict) -> NodeReadback:
    if not isinstance(d, dict) or d.get("schema") != "PK_READBACK/1":
        raise MitigationMissing("payload is not PK_READBACK/1", code="bad_request", details={})
    try:
        # The status a collector *claims* is never trusted: it is re-derived from the
        # raw kernel string with the same fail-closed classifier (checklist 25).
        obs = tuple(Observation(node=o["node"], mitigation=o["mitigation"], status=classify(o.get("raw"))[0],
                                raw=o.get("raw"),
                                reason=classify(o.get("raw"))[1] + ("" if classify(o.get("raw"))[0] == o.get("status")
                                                                     else ":claimed_status_overridden"), source=o["source"], collector_id=o["collector_id"],
                                observed_at_unix=float(o["observed_at_unix"]), observed_monotonic=0.0,
                                ttl_s=float(o["ttl_s"])) for o in d["observations"])
        if any(o.node != d["node"] for o in obs):
            raise ValueError("observation node differs from read-back node")
        if len(obs) > 256:
            raise ValueError("too many observations")
        return NodeReadback(d["node"], obs, d["smt_enabled"], d["smt_reason"], d["core_scheduling"],
                            d["core_scheduling_reason"], d["kernel"], d["machine"], d["collector_id"],
                            float(d["observed_at_unix"]), 0.0, float(d["ttl_s"]))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise MitigationMissing("malformed read-back", code="bad_request",
                                details={"error": type(exc).__name__}) from None


class PostureRegistry:
    def __init__(self, *, keys: KeyRegistry, authz: Authorizer, policy: Policy,
                 config: ConfigStore | None = None, audit: AuditLog | None = None,
                 metrics: Metrics | None = None, logger: StructuredLogger | None = None,
                 health: HealthMonitor | None = None, clock=time.time, mono=time.monotonic,
                 release_digest: str = "unbound") -> None:
        self.keys, self.authz, self.policy = keys, authz, policy
        self.config = config or ConfigStore()
        self.audit = audit or AuditLog()
        self.metrics = metrics or Metrics()
        self.log = logger or StructuredLogger(stream=_NullStream())
        self.health = health or HealthMonitor()
        self.clock, self.mono = clock, mono
        self.release_digest = release_digest
        self._lock = threading.RLock()
        self._nodes: dict[str, dict] = {}
        self._epochs: dict[str, int] = {}
        self._quarantined: dict[str, str] = {}
        self._frozen = False
        self._explain: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
        self.health.mark_ready()

    # ------------------------------------------------------------------ intake
    def submit(self, principal: str, envelope: dict, *, gap02: dict | None = None) -> dict:
        node = envelope.get("header", {}).get("node") if isinstance(envelope, dict) else None
        try:
            self.authz.check(principal, CAP_POSTURE_WRITE, node)
            payload = verify_envelope(envelope, self.keys, now=self.clock())
            rb = readback_from_dict(payload.get("readback"))
            epoch = payload.get("epoch")
            if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
                raise MitigationMissing("epoch must be a non-negative int", code="bad_request", details={})
            if rb.node != node:
                raise MitigationMissing("read-back node differs from envelope node",
                                        code="attestation_node_mismatch", details={"node": node})
            with self._lock:
                if epoch < self._epochs.get(node, -1):
                    raise MitigationMissing("read-back from an older collector epoch",
                                            code="posture_stale_epoch",
                                            details={"node": node, "epoch": epoch, "known": self._epochs[node]})
                costs = payload.get("measured_costs") or {}
                if not isinstance(costs, dict):
                    raise MitigationMissing("measured_costs must be an object", code="bad_request", details={})
                try:
                    state, notes = rb.to_state(costs)
                except (ValueError, TypeError) as exc:
                    raise MitigationMissing("read-back failed validation", code="bad_request",
                                            details={"error": str(exc)[:200]}) from None
                contradictions = gap02_contradictions(gap02 or {}, {o.mitigation: o.status for o in rb.observations})
                for c in contradictions:  # contradicted "not affected" is downgraded to unknown
                    state.record(c["mitigation"], UNKNOWN, 0.0)
                self._epochs[node] = epoch
                self._nodes[node] = {"state": state, "readback": rb, "received_mono": self.mono(),
                                     "received_unix": self.clock(), "notes": notes + contradictions,
                                     "key_id": envelope["header"]["key_id"], "digest": rb.digest(),
                                     "epoch": epoch}
        except MitigationMissing as exc:
            self._count_refusal("submit", exc, node)
            raise
        self.health.beat(f"collector:{node}")
        self.audit.append("posture_accepted", node=node, digest=rb.digest(), epoch=epoch,
                          key_id=envelope["header"]["key_id"], notes=[n["code"] for n in notes + contradictions])
        self.metrics.inc("inv43_posture_accepted_total", node=node)
        self._refresh_gauges()
        return {"node": node, "digest": rb.digest(), "notes": notes + contradictions}

    def _ttl(self, entry: dict) -> float:
        return min(entry["readback"].ttl_s, float(self.config.active["posture_ttl_s"]))

    def _fresh_entry(self, node: str) -> dict:
        with self._lock:
            entry = self._nodes.get(node)
        if entry is None:
            raise MitigationMissing(f"{node}: no attested posture", code="posture_absent", details={"node": node})
        age = (self.mono() - entry["received_mono"]) + max(0.0, entry["received_unix"] - entry["readback"].observed_at_unix)
        if age > self._ttl(entry):
            raise MitigationMissing(f"{node}: posture is stale", code="posture_stale",
                                    details={"node": node, "age_s": round(age, 3), "ttl_s": self._ttl(entry)})
        return entry

    # --------------------------------------------------------------- queries
    def status(self, principal: str, node: str, *, version: int = 1) -> dict:
        self.authz.check(principal, CAP_POSTURE_READ, node)
        entry = self._fresh_entry(node)
        rep = entry["state"].report(version=version)
        rep["freshness"] = {"collector_id": entry["readback"].collector_id, "digest": entry["digest"],
                            "observed_at_unix": entry["readback"].observed_at_unix, "epoch": entry["epoch"]}
        return rep

    # ------------------------------------------------------------- decisions
    def decide(self, principal: str, node: str, a: dict, b: dict, *, tier: str,
               traceparent: str | None = None, op_id: str | None = None) -> dict:
        trace_id, _parent, trusted = parse_traceparent(traceparent)
        decision_id = str(uuid.uuid4())
        op_id = op_id or decision_id
        t0 = self.mono()
        inputs = {"node": node, "a": a, "b": b, "tier": tier}
        req = None
        entry = None
        try:
            self.authz.check(principal, CAP_COTENANCY_DECIDE, node)
            for w in (a, b):
                if not isinstance(w, dict):
                    raise MitigationMissing("workload must be an object", code="bad_request", details={})
                _require_identifier(w.get("tenant"), "tenant")
                _require_identifier(w.get("trust_class"), "trust_class")
            same = a["tenant"] == b["tenant"]
            with self._lock:
                frozen, quarantined = self._frozen, self._quarantined.get(node)
            if frozen:
                raise MitigationMissing("placement is frozen by operator control", code="placement_frozen",
                                        details={"node": node})
            if quarantined is not None:
                raise MitigationMissing(f"{node} is quarantined", code="node_quarantined",
                                        details={"node": node, "reason": quarantined})
            if not same and not self.config.active["cross_tenant_placement_enabled"]:
                raise MitigationMissing("cross-tenant placement globally disabled", code="cross_tenant_disabled",
                                        details={})
            entry = self._fresh_entry(node) if not same else None
            lineage = (a.get("cpu_lineage") or b.get("cpu_lineage")) if not same else None
            req = self.policy.requirement(a["trust_class"], b["trust_class"], tier=tier, cpu_lineage=lineage,
                                          same_tenant=same)
            if not req.cross_tenant_allowed:
                raise MitigationMissing("policy forbids cross-tenant co-location for this pair",
                                        code="cross_tenant_forbidden_by_policy",
                                        details={"node": node, "derivation": list(req.derivation)})
            if same:
                result = {"schema": "PK_COTENANCY/1", "permitted": True,
                          "reason": "same tenant; no cross-tenant boundary to defend", "tenants": [a["tenant"]]}
            else:
                result = entry["state"].may_cotenant(a["tenant"], b["tenant"], req.mitigations)
            verdict, code = "permit", None
        except MitigationMissing as exc:
            result, verdict, code = exc.to_dict(), "refuse", exc.code
        except Exception as exc:  # defect: never let it become a permit
            result = {"schema": "PK_ERROR/1", "code": "internal_error", "message": type(exc).__name__, "details": {}}
            verdict, code = "refuse", "internal_error"
        elapsed = self.mono() - t0
        record = {
            "decision_id": decision_id, "op_id": op_id, "trace_id": trace_id, "trace_trusted": trusted,
            "verdict": verdict, "code": code,
            "failure_class": classify_code(code).value if code else None,
            "inputs_sha256": hashlib.sha256(json.dumps(inputs, sort_keys=True, default=str).encode()).hexdigest(),
            "inputs": inputs,
            "posture": None if entry is None else {"digest": entry["digest"], "epoch": entry["epoch"],
                                                   "key_id": entry["key_id"],
                                                   "report": entry["state"].report(version=2),
                                                   "notes": entry["notes"]},
            "policy": None if req is None else req.to_dict(),
            "config": self.config.provenance,
            "release": {"component": "INV-43", "version": __version__, "digest": self.release_digest},
            "result": result,
        }
        with self._lock:
            self._explain[decision_id] = record
            while len(self._explain) > MAX_EXPLAIN:
                self._explain.popitem(last=False)
        self.audit.append("cotenancy_decision", decision_id=decision_id, node=node, verdict=verdict, code=code,
                          inputs_sha256=record["inputs_sha256"],
                          policy_digest=None if req is None else req.policy_digest)
        self.metrics.inc("inv43_decisions_total", verdict=verdict, code=code or "ok")
        if code:
            self.metrics.inc("inv43_refusals_total", failure_class=classify_code(code).value, code=code)
        self.metrics.observe("inv43_decision_seconds", elapsed)
        tenants = [x.get("tenant") for x in (a, b) if isinstance(x, dict) and isinstance(x.get("tenant"), str)]
        self.log.log("info" if verdict == "permit" else "warning", "cotenancy_decision", node=node,
                     tenants=tenants, workload=a.get("id") if isinstance(a, dict) else None,
                     op_id=op_id, trace_id=trace_id, verdict=verdict, code=code, decision_id=decision_id)
        out = dict(result)
        out["decision_id"] = decision_id
        return out

    def explain(self, principal: str, decision_id: str) -> dict:
        with self._lock:
            rec = self._explain.get(decision_id)
        node = None if rec is None else rec["inputs"]["node"]
        self.authz.check(principal, CAP_EXPLAIN, node)
        if rec is None:
            raise MitigationMissing("unknown or expired decision id", code="bad_request",
                                    details={"decision_id": decision_id})
        return json.loads(json.dumps(rec, default=str))

    # -------------------------------------------------------------- controls
    def quarantine(self, principal: str, node: str, reason: str) -> None:
        self.authz.check(principal, CAP_CONTROL, node)
        _require_identifier(node, "node")
        _require_identifier(reason, "reason")
        with self._lock:
            self._quarantined[node] = reason
        self.audit.append("control_quarantine", node=node, reason=reason, by=principal)
        self._refresh_gauges()

    def release(self, principal: str, node: str) -> None:
        self.authz.check(principal, CAP_CONTROL, node)
        with self._lock:
            self._quarantined.pop(node, None)
        self.audit.append("control_release", node=node, by=principal)
        self._refresh_gauges()

    def freeze(self, principal: str, frozen: bool = True) -> None:
        self._check_global_control(principal)
        with self._lock:
            self._frozen = bool(frozen)
        self.health.set_frozen(bool(frozen))
        self.audit.append("control_freeze" if frozen else "control_unfreeze", by=principal)

    def _check_global_control(self, principal: str) -> None:
        # Global controls need an unscoped operator: a node-scoped principal cannot freeze the fleet.
        p = self.authz._p.get(principal)
        if p is None or p.node_scope is not None:
            from .authz import AuthzDenied
            raise AuthzDenied(str(principal), CAP_CONTROL, "*global*")
        self.authz.check(principal, CAP_CONTROL, None)

    def restore_controls(self, entries: list[dict]) -> dict:
        """Rebuild quarantine/freeze from a verified audit chain after restart."""
        q: dict[str, str] = {}
        frozen = False
        for e in entries:
            body = e["body"]
            k = body["kind"]
            if k == "control_quarantine":
                q[body["node"]] = body["reason"]
            elif k == "control_release":
                q.pop(body["node"], None)
            elif k == "control_freeze":
                frozen = True
            elif k == "control_unfreeze":
                frozen = False
        with self._lock:
            self._quarantined, self._frozen = q, frozen
        self.health.set_frozen(frozen)
        return {"quarantined": sorted(q), "frozen": frozen}

    # ------------------------------------------------------------ telemetry
    def _count_refusal(self, op: str, exc: MitigationMissing, node) -> None:
        self.metrics.inc("inv43_refusals_total", failure_class=classify_code(exc.code).value, code=exc.code)
        self.audit.append("refusal", op=op, node=node, code=exc.code)

    def _refresh_gauges(self) -> None:
        with self._lock:
            entries = list(self._nodes.items())
            self.metrics.set("inv43_quarantined_nodes", len(self._quarantined))
        smt_unsafe = 0
        for node, e in entries:
            st: MitigationState = e["state"]
            if st.smt_enabled and not st.core_scheduling:
                smt_unsafe += 1
            for name, (status, cost) in st.snapshot().items():
                self.metrics.set("inv43_mitigation_cost_percent", cost, node=node, mitigation=name)
        self.metrics.set("inv43_smt_unsafe_nodes", smt_unsafe)
        self.metrics.set("inv43_nodes_with_posture", len(entries))

    def degraded_nodes(self) -> list[str]:
        out = []
        with self._lock:
            nodes = list(self._nodes)
        for n in nodes:
            try:
                self._fresh_entry(n)
            except MitigationMissing:
                out.append(n)
        return out
