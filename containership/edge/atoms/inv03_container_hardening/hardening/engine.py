"""The 4.3.0 decision engine: evaluate, explain, audit, emit, and act.

Checklist items served: 4 (fail-closed runtime selection), 16 (drift
reconciliation), 17 (quarantine plan), 18 (emergency deny-all switch),
42 (explain object), 43 (release lineage fields on each decision), and the
wiring of items 26/38/39/40/41 into every decision.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Mapping

from .authority import AuthError, Authorizer, ExceptionStore, Principal
from .baseline import BaselineError, BaselineStore, resolve_settings
from .controls import CONTROLS_43, all_containers
from .core import AuditLedger, ClockUntrusted, Reason, TrustedClock, digest
from .runtime import RuntimeInventory
from .telemetry import Metrics, StructuredLogger, child_traceparent

DECISION_SCHEMA = "PK_HARDEN_EVAL/2"
MAX_SPEC_BYTES = 256 * 1024
MAX_CONTAINERS = 64


def _size_ok(obj: object, budget: list[int], depth: int = 0) -> bool:
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        return False
    if isinstance(obj, Mapping):
        return all(isinstance(k, str) and _size_ok(v, budget, depth + 1) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return all(_size_ok(v, budget, depth + 1) for v in obj)
    if isinstance(obj, str):
        budget[0] -= len(obj) // 64
        return budget[0] >= 0
    return obj is None or isinstance(obj, (bool, int, float))


class Engine:
    def __init__(self, baselines: BaselineStore, exceptions: ExceptionStore, clock: TrustedClock,
                 ledger: AuditLedger, runtimes: RuntimeInventory, authz: Authorizer,
                 metrics: Metrics | None = None, logger: StructuredLogger | None = None):
        self.baselines, self.exceptions, self.clock = baselines, exceptions, clock
        self.ledger, self.runtimes, self.authz = ledger, runtimes, authz
        self.metrics = metrics or Metrics()
        self.logger = logger or StructuredLogger()
        self._emergency = False
        self._admitted: dict[str, dict] = {}
        self._lock = threading.Lock()

    # -- item 18 -------------------------------------------------------------
    def set_emergency(self, p: Principal, on: bool, reason: str) -> None:
        """Deny-all kill switch. There is deliberately no admit-all mode."""
        self.authz.require(p, "emergency.toggle")
        if not isinstance(reason, str) or not reason.strip():
            raise AuthError("MALFORMED_INPUT", "emergency toggle needs a reason")
        self._emergency = bool(on)
        self.metrics.set("inv03_emergency_deny_all", 1 if on else 0)
        self.ledger.append("emergency.toggle", "INV-03", p.subject, self.clock.now(),
                           {"on": bool(on), "reason": reason})

    # -- the decision --------------------------------------------------------
    def decide(self, request: Mapping[str, Any], principal: Principal | None = None) -> dict:
        t0 = time.perf_counter()
        trace_id, span_id, tp = child_traceparent(request.get("traceparent") if isinstance(request, Mapping) else None)
        try:
            out = self._decide(request, principal)
        except Exception as exc:  # any defect is a denial, never an admission
            out = self._deny(Reason.INTERNAL, [f"internal defect: {type(exc).__name__}"], request)
        out["trace"] = {"trace_id": trace_id, "span_id": span_id, "traceparent": tp}
        ms = (time.perf_counter() - t0) * 1000
        self.metrics.observe_ms(ms)
        self.metrics.inc("inv03_decisions_total", reason=out["reason"])
        for c in out.get("failed", []):
            self.metrics.inc("inv03_denials_total", control=c)
        self.logger.log("info" if out["admit"] else "warn", "decision",
                        decision_id=out["decision_id"], workload=out["workload"], tenant=out["scope"].get("tenant"),
                        reason=out["reason"], failed=out.get("failed", []), trace_id=trace_id)
        try:
            self.ledger.append("decision", out["workload"], principal.subject if principal else "anonymous",
                               out.get("at") or 0, {"decision_id": out["decision_id"], "admit": out["admit"],
                                                     "reason": out["reason"], "failed": out.get("failed", []),
                                                     "baseline_digest": out.get("baseline_digest")})
        except Exception:
            # Audit is mandatory: a decision that cannot be recorded is not an admission.
            if out["admit"]:
                out = self._deny(Reason.DEPENDENCY_FAILURE, ["audit ledger unavailable"], request)
                out["trace"] = {"trace_id": trace_id, "span_id": span_id, "traceparent": tp}
        return out

    def _deny(self, reason: str, errors: list[str], request: object, **extra) -> dict:
        wl = request.get("workload") if isinstance(request, Mapping) else None
        raw_scope = request.get("scope") if isinstance(request, Mapping) else None
        scope: Mapping = raw_scope if isinstance(raw_scope, Mapping) else {}
        body = {"schema": DECISION_SCHEMA, "admit": False, "reason": reason,
                "workload": wl if isinstance(wl, str) else "<invalid>", "scope": dict(scope),
                "failed": [], "excepted": [], "errors": errors}
        body.update(extra)
        body["decision_id"] = digest({"b": body, "n": time.time_ns()})[7:31]
        return body

    def _decide(self, req: Mapping[str, Any], principal: Principal | None) -> dict:
        if not isinstance(req, Mapping):
            return self._deny(Reason.MALFORMED_INPUT, ["request must be an object"], {})
        if principal is not None:
            try:
                self.authz.require(principal, "evaluate")
            except AuthError as e:
                return self._deny(Reason.UNAUTHORIZED, [str(e)], req)
        if self._emergency:
            return self._deny(Reason.EMERGENCY_DENY, ["emergency deny-all is active"], req)
        wl, pod, scope = req.get("workload"), req.get("pod"), req.get("scope")
        errs = []
        if not isinstance(wl, str) or not wl.strip() or len(wl) > 253:
            errs.append("workload must be a non-blank string <= 253 chars")
        if not isinstance(pod, Mapping):
            errs.append("pod must be an object")
        elif not _size_ok(pod, [MAX_SPEC_BYTES // 8]):
            errs.append("pod spec too large, too deep, or not JSON-shaped")
        elif not all_containers(pod):
            errs.append("pod has no containers")
        elif len(all_containers(pod)) > MAX_CONTAINERS:
            errs.append("too many containers")
        if not isinstance(scope, Mapping) or not all(isinstance(scope.get(k), str) and scope.get(k)
                                                      for k in ("tenant", "environment", "site")):
            errs.append("scope needs tenant, environment and site")
        if errs:
            return self._deny(Reason.MALFORMED_INPUT, errs, req)
        if not (isinstance(wl, str) and isinstance(pod, Mapping) and isinstance(scope, Mapping)):  # -O safe
            return self._deny(Reason.INTERNAL, ["validation invariant broken"], req)
        try:
            now = self.clock.now()
        except ClockUntrusted as e:
            return self._deny(Reason.CLOCK_UNTRUSTED, [str(e)], req)
        try:
            active = self.baselines.active()
        except BaselineError as e:
            return self._deny(Reason.BASELINE_UNAVAILABLE, [str(e)], req)
        if active is None:
            return self._deny(Reason.BASELINE_UNAVAILABLE, ["no active baseline"], req)
        epoch, doc = active
        try:
            settings = resolve_settings(doc, scope["tenant"], scope["environment"], scope["site"])
        except BaselineError as e:
            return self._deny(Reason.UNSUPPORTED, [str(e)], req)
        ctx = dict(settings)
        raw_facts = req.get("facts")
        facts: Mapping = raw_facts if isinstance(raw_facts, Mapping) else {}
        ctx.update({k: v for k, v in facts.items()
                    if k in ("namespace_default_deny", "resolved_uids", "node_pid_limit")})
        # item 4: runtime selection must resolve to a healthy, approved sandbox runtime
        rc = pod.get("runtimeClassName")
        rt_ok, rt_msg = self.runtimes.check(rc, req.get("node"))
        failed, excepted, findings = [], [], {}
        for name in doc["controls"]:
            try:
                v = list(CONTROLS_43[name](pod, ctx))
            except Exception as exc:
                v = [f"control raised {type(exc).__name__}"]
            if name == "sandbox-runtime" and not v and not rt_ok:
                v = [rt_msg]
            if not v:
                continue
            findings[name] = v
            exc_rec = self.exceptions.active_for(wl.strip(), name, now)
            if exc_rec and name != "sandbox-runtime":  # the sandbox itself is never waivable
                excepted.append({"control": name, "exception_id": exc_rec["id"], "expires": exc_rec["expires"]})
            else:
                failed.append(name)
        admit = not failed
        reason = Reason.ADMIT if admit else (Reason.RUNTIME_UNAVAILABLE if failed == ["sandbox-runtime"] and not rt_ok
                                             else Reason.POLICY_REJECTED)
        body = {
            "schema": DECISION_SCHEMA, "admit": admit, "reason": reason, "workload": wl.strip(),
            "scope": dict(scope), "at": now, "baseline_version": doc["version"],
            "baseline_digest": digest(doc), "baseline_epoch": epoch,
            "failed": failed, "excepted": excepted, "errors": [],
            "explain": {  # item 42
                "controls_evaluated": list(doc["controls"]),
                "findings": findings,
                "inputs_digest": digest(pod),
                "settings_digest": digest(settings),
                "runtime": {"class": rc, "ok": rt_ok, "detail": rt_msg},
            },
            "lineage": {  # item 43: carried through, never invented
                k: req.get("lineage", {}).get(k) for k in
                ("release", "image_digests", "deployment_revision", "node", "topology_ref")
            } if isinstance(req.get("lineage"), Mapping) else {},
        }
        body["decision_id"] = digest({"w": body["workload"], "at": now, "i": digest(pod), "n": time.time_ns()})[7:31]
        if admit:
            with self._lock:
                self._admitted[wl.strip()] = {"inputs_digest": digest(pod), "baseline_digest": body["baseline_digest"],
                                              "runtime": rc, "decision_id": body["decision_id"]}
        return body

    # -- item 16 / 17 ---------------------------------------------------------
    def reconcile(self, workload: str, observed_pod: Mapping, observed_runtime_handler: str | None) -> dict:
        """Compare what is running with what was admitted; propose containment on drift."""
        with self._lock:
            admitted = self._admitted.get(workload)
        if admitted is None:
            return {"workload": workload, "drift": True, "why": ["never admitted by INV-03"],
                    "action": self.quarantine_plan(workload, "unadmitted workload running")}
        why = []
        if digest(observed_pod) != admitted["inputs_digest"]:
            why.append("running spec differs from admitted spec")
        expected_handler = self.runtimes.handler_for(admitted["runtime"])
        if observed_runtime_handler != expected_handler:
            why.append(f"runtime handler {observed_runtime_handler!r} != admitted {expected_handler!r}")
        return {"workload": workload, "drift": bool(why), "why": why,
                "action": self.quarantine_plan(workload, "; ".join(why)) if why else None}

    def quarantine_plan(self, workload: str, reason: str) -> dict:
        """A deterministic, orchestrator-neutral containment plan. Executing it
        against a real cluster is the host adapter's job (item 17 integration
        evidence is BLOCKED without a cluster)."""
        return {"schema": "INV03_QUARANTINE/1", "workload": workload, "reason": reason, "steps": [
            {"op": "label", "value": "inv03.quarantine=true"},
            {"op": "network_isolate", "value": "apply deny-all NetworkPolicy selecting inv03.quarantine=true"},
            {"op": "freeze", "value": "cgroup freeze (kubectl debug / crictl pause)"},
            {"op": "preserve_evidence", "value": "snapshot spec, logs, runtime state to audit ledger"},
            {"op": "terminate", "value": "evict after evidence capture unless incident commander holds"},
        ]}
