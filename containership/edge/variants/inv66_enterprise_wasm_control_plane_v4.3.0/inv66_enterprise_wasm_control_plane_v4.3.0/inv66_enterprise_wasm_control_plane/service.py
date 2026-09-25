"""INV-66 production control-plane service.

Composes every production control around the audit journal, which is the
single source of truth: *all* state (decisions, lifecycle, inventory, outbox,
freezes, idempotency records, configuration history) is a pure reduction of
journalled entries, and every mutation is journalled (fsync) **before** it
takes effect.  Consequently:

* restart = replay (snapshot + journal) -> identical state (MC-038);
* nothing is delivered to INV-63 unless an ``admission`` entry with
  ``admitted: true`` is durable and the scope is not frozen (guardrail SLO);
* if the journal cannot be written the request fails closed.

Public operations and the capability each requires on its scope:

========================  ==================  ===============================
operation                 capability          scope
========================  ==================  ===============================
admit                     admit               org/tenant/lattice
apply_config / rollback   config.activate     org
set_freeze                freeze              the frozen scope
transition                lifecycle.transition decision's lattice
audit_query / export      audit.read/.export  org
inventory                 inventory.read      org or tenant
explain                   decision.read       decision's lattice
========================  ==================  ===============================
"""
from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any, Callable

from . import __version__
from .adapters import DeploymentManager, PolicyDecision, PolicyEngine
from .canonical import canonical_json, digest, hmac_hex
from .config import PolicySet, build_policy
from .errors import ControlPlaneError, Error, fail
from .identity import Authenticator, Principal
from .lifecycle import OPERATOR_TRANSITIONS, legal
from .observability import JsonLogger, Metrics, new_traceparent, parse_traceparent
from .rbac import ROLE_CAPABILITIES, contains, effective_access, scope_of
from .resilience import Bulkhead, CircuitBreaker, Deadline, RetryPolicy, TokenBucket, call_with_policy
from .schema import validate
from .store import JournalStore

ADMIT_PROTOCOLS = ("PK_ECP_ADMIT/1",)
REQUEST_SCHEMA = "urn:inv66:schema:PK_ECP_ADMIT:1:request"
EXPORT_DOMAIN = b"PK_ECP_EXPORT/1\0"
DECISION_CACHE = 20_000        # decisions kept in memory; older terminal ones are served from the journal
PRUNABLE = ("rejected", "deployed", "rolled_back")


def _depth_exceeds(value: Any, limit: int) -> bool:
    """Iterative depth probe (no recursion, so hostile nesting cannot crash us)."""
    stack = [(value, 1)]
    while stack:
        v, d = stack.pop()
        if isinstance(v, (dict, list)):
            if d > limit:
                return True
            stack.extend((c, d + 1) for c in (v.values() if isinstance(v, dict) else v))
    return False


def empty_state() -> dict:
    return {"decisions": {}, "inventory": {}, "idem": {}, "outbox": {}, "freezes": {},
            "config": {"active": None, "history": [], "docs": {}}}


class ControlPlaneService:
    def __init__(self, *, org: str, store: JournalStore, authenticator: Authenticator, initial_config: dict | None,
                 policy_engine: PolicyEngine, deployer: DeploymentManager, metrics: Metrics | None = None,
                 logger: JsonLogger | None = None, clock: Callable[[], float] = time.time,
                 mono: Callable[[], float] = time.monotonic, bootstrap_principal: str = "service:bootstrap",
                 sleep: Callable[[float], None] = time.sleep):
        self.org = org
        self.store = store
        self.authn = authenticator
        self.policy_engine = policy_engine
        self.deployer = deployer
        self.metrics = metrics or Metrics()
        self.log = logger or JsonLogger()
        self.clock, self.mono, self.sleep = clock, mono, sleep
        self._lock = threading.RLock()
        self.policy_breaker = CircuitBreaker("policy-engine", clock=mono)
        self.deploy_breaker = CircuitBreaker("deployment-manager", clock=mono)
        self.retry = RetryPolicy()
        self.buckets = TokenBucket(clock=mono)
        self.started_at = clock()
        self.state = empty_state()
        self.policy: PolicySet | None = None
        self.compaction_due = threading.Event()
        self.decision_cache = DECISION_CACHE
        self.dependency_status: dict[str, str] = {"store": "ok", "policy-engine": "unknown",
                                                  "deployment-manager": "unknown", "identity": "ok"}
        self._replay()
        self.store.acquire()
        if self.policy is None:
            if initial_config is None:
                raise fail("CONFIG_INVALID", "no active configuration and no initial configuration supplied")
            self._activate(build_policy(initial_config), bootstrap_principal, "bootstrap")
        self.bulkhead = Bulkhead(self.policy.max_inflight)

    # ================================================================ state
    def _replay(self) -> None:
        snap = self.store.load_snapshot()
        self.state = copy.deepcopy(snap["state"]) if snap else empty_state()
        for rec in self.store.records():
            self._apply(rec["entry"], rec["sequence"])
        active = self.state["config"]["active"]
        if active:
            self.policy = build_policy(self.state["config"]["docs"][active])

    def _journal(self, entry: dict) -> dict:
        entry = dict(entry, ts=self.clock())
        try:
            rec = self.store.append(entry)
        except ControlPlaneError:
            self.dependency_status["store"] = "failed"
            self.metrics.inc("inv66_store_failures")
            raise
        self.dependency_status["store"] = "ok"
        self._apply(rec["entry"], rec["sequence"])
        self.metrics.inc("inv66_audit_entries", kind=entry["kind"])
        if self.policy is not None:
            n = len(self.store._records)
            if n >= 2 * self.policy.audit_retention_records:   # maintenance fell behind: backpressure inline
                self.compact()
            elif n >= self.policy.audit_retention_records:
                self.compaction_due.set()
        return rec

    def _apply(self, e: dict, seq: int) -> None:
        """Pure reducer: state <- f(state, entry).  Must stay deterministic."""
        st, kind = self.state, e["kind"]
        if kind == "config":
            st["config"]["docs"].setdefault(e["digest"], e["document"]) if "document" in e else None
            st["config"]["active"] = e["digest"]
            st["config"]["history"].append({"sequence": seq, "digest": e["digest"], "revision": e["revision"],
                                            "author": e["author"], "approved_by": e.get("approved_by", []),
                                            "source_revision": e.get("source_revision"), "actor": e["actor"],
                                            "action": e["action"], "ts": e["ts"]})
        elif kind == "admission":
            d = {k: e[k] for k in ("decision_id", "request_id", "principal", "tenant", "lattice", "admitted",
                                   "errors", "manifest_sha256", "policy_version", "config_digest", "trace_id",
                                   "component_count")}
            d.update(sequence=seq, ts=e["ts"], state="admitted" if e["admitted"] else "rejected",
                     history=[{"state": "proposed", "sequence": seq},
                              {"state": "admitted" if e["admitted"] else "rejected", "sequence": seq}])
            st["decisions"][e["decision_id"]] = d
            cap = getattr(self, "decision_cache", DECISION_CACHE)
            if len(st["decisions"]) > cap:
                for old in list(st["decisions"])[: len(st["decisions"]) - cap + 64]:
                    if st["decisions"][old]["state"] in PRUNABLE:
                        del st["decisions"][old]
                    if len(st["decisions"]) <= cap:
                        break
            if e.get("idempotency_key"):
                st["idem"][e["idempotency_key"]] = {"request_digest": e["request_digest"],
                                                    "decision_id": e["decision_id"], "ts": e["ts"]}
            if e["admitted"]:
                st["outbox"][e["decision_id"]] = {"lattice": e["lattice"], "manifest": e["manifest"],
                                                  "attempts": 0, "tenant": e["tenant"]}
                inv = st["inventory"].setdefault(f"{e['tenant']}/{e['lattice']}", {})
                for c in e["manifest"]["components"]:
                    inv[c["name"]] = {"image": c["image"], "signer": c["signer"], "decision_id": e["decision_id"],
                                      "sequence": seq}
        elif kind == "lifecycle":
            d = st["decisions"][e["decision_id"]]
            d["state"] = e["to"]
            d["history"].append({"state": e["to"], "sequence": seq, "actor": e.get("actor"), "reason": e.get("reason")})
            if e["to"] in ("deployed", "rolled_back", "quarantined"):
                st["outbox"].pop(e["decision_id"], None)
            if e["to"] == "admitted" and e.get("requeue"):
                st["outbox"][e["decision_id"]] = e["requeue"]
            if e["to"] == "delivery_failed" and e["decision_id"] in st["outbox"]:
                st["outbox"][e["decision_id"]]["attempts"] += 1
            if e["to"] == "rolled_back":
                inv = st["inventory"].get(f"{d['tenant']}/{d['lattice']}", {})
                for name in [n for n, v in inv.items() if v["decision_id"] == e["decision_id"]]:
                    del inv[name]
        elif kind == "freeze":
            if e["on"]:
                st["freezes"][e["scope"]] = {"actor": e["actor"], "reason": e["reason"], "sequence": seq,
                                             "ticket": e.get("ticket"), "expires_at": e.get("expires_at"),
                                             "since": e["ts"]}
            else:
                st["freezes"].pop(e["scope"], None)
        elif kind in ("anchor", "maintenance"):
            pass

    def snapshot_state(self) -> dict:
        with self._lock:
            return copy.deepcopy(self.state)

    # ================================================================ authz
    def _principal(self, token: str | None, peer: str | None) -> Principal:
        try:
            return self.authn.authenticate(token, peer_thumbprint=peer)
        except ControlPlaneError as exc:
            self.metrics.inc("inv66_authn_failures", code=exc.error.code)
            raise

    def _authorize(self, p: Principal, capability: str, scope: str) -> None:
        r = self.policy.rbac.check(p.subject, capability, scope, int(self.clock()), p.groups)
        if not r.allowed:
            self.metrics.inc("inv66_rbac_denials", capability=capability)
            raise fail("AUTHZ_EXPLICIT_DENY" if r.explicit_deny else "AUTHZ_DENIED",
                       f"{p.subject} lacks {capability} on {scope}", target=scope)

    def frozen_by(self, scope: str) -> str | None:
        now = self.clock()
        for s, f in self.state["freezes"].items():
            if contains(s, scope) and (f.get("expires_at") is None or now < f["expires_at"]):
                return s
        return None

    def access_review(self, token: str, subject: str, scope: str, groups: tuple[str, ...] = (), *, peer=None) -> dict:
        p = self._principal(token, peer)
        self._authorize(p, "audit.read", scope_of(self.org))
        return effective_access(self.policy.rbac, subject, scope, int(self.clock()), groups)

    # ================================================================ admit
    def admit(self, token: str | None, request: Any, *, traceparent: str | None = None,
              peer: str | None = None) -> dict:
        t0 = self.mono()
        tp = parse_traceparent(traceparent)
        trace_id, span_id, child_tp = new_traceparent(tp[0] if tp else None)
        outcome = "error"
        try:
            with self.bulkhead:
                resp = self._admit(token, request, trace_id, child_tp, peer)
                outcome = "admitted" if resp["admitted"] else "rejected"
                return resp
        except ControlPlaneError as exc:
            outcome = exc.error.code
            raise
        finally:
            ms = (self.mono() - t0) * 1000
            self.metrics.inc("inv66_admissions", outcome=outcome)
            self.metrics.observe_ms("inv66_admission_latency_ms", ms)
            self.log.log("info", "admission", trace_id=trace_id, span_id=span_id, outcome=outcome,
                         duration_ms=round(ms, 3),
                         request_id=request.get("request_id") if isinstance(request, dict) else None,
                         tenant=request.get("tenant") if isinstance(request, dict) else None,
                         lattice=request.get("lattice") if isinstance(request, dict) else None)

    def _admit(self, token, request, trace_id, traceparent, peer) -> dict:
        principal = self._principal(token, peer)
        if not self.is_leader():
            raise fail("NOT_LEADER", "this instance does not hold the leader lease")
        if isinstance(request, dict) and request.get("protocol") not in ADMIT_PROTOCOLS and "protocol" in request:
            raise fail("PROTOCOL_UNSUPPORTED", f"supported: {list(ADMIT_PROTOCOLS)}")
        if _depth_exceeds(request, 32):
            raise fail("SCHEMA_INVALID", "request nesting deeper than 32 levels")
        try:
            raw_size = len(canonical_json(request))
        except (TypeError, ValueError, OverflowError, RecursionError):
            raise fail("SCHEMA_INVALID", "request is not finite JSON data") from None
        pol = self.policy
        if raw_size > pol.max_manifest_bytes + 16_384:
            raise fail("MANIFEST_TOO_LARGE", f"request exceeds {pol.max_manifest_bytes} bytes")
        violations = validate(request, REQUEST_SCHEMA)
        if violations:
            raise fail("SCHEMA_INVALID", "request does not match PK_ECP_ADMIT/1", violations=violations[:20])
        deadline = Deadline(request.get("deadline_ms", 5000) / 1000.0, self.mono)
        tenant, lattice = request["tenant"], request["lattice"]
        scope = scope_of(self.org, tenant, lattice)
        env = request.get("environment", pol.environment)
        if env != pol.environment:
            raise fail("POLICY_DENIED", f"this control plane serves {pol.environment}, not {env}", rule="environment")
        frozen = self.frozen_by(scope)
        if frozen:
            raise fail("FROZEN", f"{frozen} is frozen", target=frozen, freeze=self.state["freezes"][frozen])
        self._authorize(principal, "admit", scope)

        req_digest = digest(request | {"request_id": None, "deadline_ms": None})
        key = request.get("idempotency_key")
        with self._lock:
            if key:
                prior = self.state["idem"].get(key)
                if prior and self.clock() - prior["ts"] <= pol.idempotency_ttl_s:
                    if prior["request_digest"] != req_digest:
                        raise fail("IDEMPOTENCY_CONFLICT", "idempotency key reused with a different body")
                    return self._response(self.state["decisions"][prior["decision_id"]], replayed=True)

        quota = pol.quotas.get(f"{tenant}/{lattice}", pol.quotas.get(tenant, pol.quotas.get("*")))
        if quota is not None and not self.buckets.take(f"{tenant}/{lattice}", quota):
            raise fail("QUOTA_EXCEEDED", f"quota {quota}/min exhausted for {tenant}/{lattice}")

        manifest = request["manifest"]
        errors: list[Error] = []
        encoded = canonical_json(manifest)
        if len(encoded) > pol.max_manifest_bytes:
            errors.append(Error("MANIFEST_TOO_LARGE", f"manifest exceeds {pol.max_manifest_bytes} bytes"))
        comps = manifest["components"]
        if len(comps) > pol.max_components:
            errors.append(Error("MANIFEST_TOO_MANY_COMPONENTS", f"{len(comps)} > {pol.max_components}"))
        seen: set[str] = set()
        now = int(self.clock())
        for i, c in enumerate(comps[: pol.max_components]):
            label = c["name"]
            if label in seen:
                errors.append(Error("COMPONENT_DUPLICATE", "duplicate component name", label))
            seen.add(label)
            errors.extend(pol.provenance.verify_component(c, label, now))

        policy_version = "n/a"
        if not errors:
            deadline.check("admission")
            pdoc = {"org": self.org, "tenant": tenant, "lattice": lattice, "environment": env,
                    "principal": principal.subject, "groups": sorted(principal.groups), "manifest": manifest}
            try:
                pd: PolicyDecision = call_with_policy(
                    lambda: self.policy_engine.evaluate(pdoc, max(0.001, deadline.remaining()), traceparent),
                    self.policy_breaker, self.retry, deadline, "POLICY_UNAVAILABLE", sleep=self.sleep)
                self.dependency_status["policy-engine"] = "ok"
                policy_version = pd.policy_version
                if not pd.allowed:
                    errors.append(Error("POLICY_DENIED", pd.message, None, {"rule": pd.rule}))
            except ControlPlaneError as exc:
                self.dependency_status["policy-engine"] = "degraded" if exc.error.code == "POLICY_UNAVAILABLE" else "ok"
                errors.append(exc.error)            # fail closed; decision is still recorded

        admitted = not errors
        decision_id = str(uuid.uuid4())
        entry = {"kind": "admission", "decision_id": decision_id, "request_id": request["request_id"],
                 "idempotency_key": key, "request_digest": req_digest, "principal": principal.subject,
                 "principal_issuer": principal.issuer, "tenant": tenant, "lattice": lattice, "admitted": admitted,
                 "errors": [e.to_dict() for e in errors], "manifest_sha256": digest(manifest),
                 "manifest_bytes": len(encoded), "component_count": len(comps), "policy_version": policy_version,
                 "config_digest": pol.digest, "config_revision": pol.revision, "trace_id": trace_id,
                 "manifest": manifest if admitted else None}
        with self._lock:
            self._journal(entry)                     # fails closed on store error
            d = self.state["decisions"][decision_id]
        if admitted:
            self.dispatch(decision_id, deadline, traceparent)
        return self._response(self.state["decisions"][decision_id], replayed=False)

    def _response(self, d: dict, replayed: bool) -> dict:
        return {"protocol": "PK_ECP_ADMIT/1", "request_id": d["request_id"], "decision_id": d["decision_id"],
                "admitted": d["admitted"], "state": "admitted" if d["admitted"] else "rejected",
                "lifecycle_state": d["state"], "errors": copy.deepcopy(d["errors"]),
                "manifest_sha256": d["manifest_sha256"], "policy_version": d["policy_version"],
                "config_digest": d["config_digest"], "audit_sequence": d["sequence"], "replayed": replayed,
                "trace_id": d["trace_id"]}

    # ============================================================= delivery
    def dispatch(self, decision_id: str, deadline: Deadline | None = None, traceparent: str | None = None) -> str:
        """Deliver one outbox item to INV-63 (at-least-once, idempotent by decision id)."""
        with self._lock:
            item = self.state["outbox"].get(decision_id)
            d = self.state["decisions"].get(decision_id)
            if item is None or d is None or not d["admitted"] or d["state"] not in ("admitted", "delivery_failed", "delivering"):
                return "skipped"
            if self.frozen_by(scope_of(self.org, d["tenant"], d["lattice"])):
                return "frozen"
            if d["state"] != "delivering":      # "delivering" = crashed mid-delivery; resume idempotently
                self._journal({"kind": "lifecycle", "decision_id": decision_id, "to": "delivering", "actor": "system"})
        deadline = deadline or Deadline(5.0, self.mono)
        traceparent = traceparent or new_traceparent(d["trace_id"])[2]
        try:
            ack = call_with_policy(lambda: self.deployer.deliver(decision_id, item["lattice"], item["manifest"],
                                                                 max(0.001, deadline.remaining()), traceparent),
                                   self.deploy_breaker, self.retry, deadline, "DEPLOY_FAILED", sleep=self.sleep)
            ok = ack.accepted and ack.delivery_id == decision_id
        except ControlPlaneError:
            ok = False
        self.dependency_status["deployment-manager"] = "ok" if ok else "degraded"
        with self._lock:
            self._journal({"kind": "lifecycle", "decision_id": decision_id,
                           "to": "deployed" if ok else "delivery_failed", "actor": "system"})
        self.metrics.inc("inv66_deliveries", outcome="ok" if ok else "failed")
        return "deployed" if ok else "delivery_failed"

    def drain_outbox(self) -> dict[str, str]:
        return {i: self.dispatch(i) for i in list(self.state["outbox"])}

    @property
    def forwarded(self) -> list[str]:
        """Decision ids whose manifests INV-63 acknowledged."""
        return [i for i, d in self.state["decisions"].items() if d["state"] == "deployed"]

    # ============================================================ admin ops
    def _activate(self, pol: PolicySet, actor: str, action: str) -> None:
        with self._lock:
            known = pol.digest in self.state["config"]["docs"]
            doc = pol.document
            self._journal({"kind": "config", "action": action, "actor": actor, "digest": pol.digest,
                           "revision": pol.revision, "author": doc["author"], "approved_by": doc.get("approved_by", []),
                           "source_revision": doc["source_revision"], **({} if known else {"document": doc})})
            self.policy = pol                       # atomic reference swap
            if hasattr(self, "bulkhead") and self.bulkhead.limit != pol.max_inflight:
                self.bulkhead = Bulkhead(pol.max_inflight)

    def apply_config(self, token: str, doc: dict, *, if_match: str | None = None, peer: str | None = None) -> dict:
        p = self._principal(token, peer)
        self._authorize(p, "config.activate", scope_of(self.org))
        pol = build_policy(doc)                    # full validation before anything changes
        cur = self.policy
        if if_match is not None and if_match != cur.digest:
            raise fail("STALE_REVISION", "active configuration changed since it was read", active=cur.version)
        now = int(self.clock())
        existing = {(b.subject, b.role, b.scope, b.effect) for b in cur.rbac.bindings}
        for b in pol.rbac.bindings:                # no privilege escalation through configuration
            if b.effect == "allow" and (b.subject, b.role, b.scope, b.effect) not in existing:
                for cap in ROLE_CAPABILITIES[b.role]:
                    if not cur.rbac.check(p.subject, cap, b.scope, now, p.groups).allowed:
                        raise fail("PRIVILEGE_ESCALATION", f"{p.subject} cannot grant {b.role} on {b.scope} (lacks {cap})")
        high = max(h["revision"] for h in self.state["config"]["history"])
        if pol.revision <= high:
            raise fail("CONFIG_INVALID", f"revision must exceed every prior revision (highest r{high})")
        self._activate(pol, p.subject, "activate")
        return {"active": pol.version, "previous": cur.version}

    def rollback_config(self, token: str, revision: int, *, peer: str | None = None) -> dict:
        p = self._principal(token, peer)
        self._authorize(p, "config.activate", scope_of(self.org))
        match = [h for h in self.state["config"]["history"] if h["revision"] == revision]
        if not match:
            raise fail("NOT_FOUND", f"revision {revision} never activated")
        pol = build_policy(self.state["config"]["docs"][match[-1]["digest"]])
        self._activate(pol, p.subject, "rollback")
        return {"active": pol.version}

    def set_freeze(self, token: str, scope: str, on: bool, reason: str, *, ticket: str | None = None,
                   ttl_s: int | None = None, peer: str | None = None) -> dict:
        p = self._principal(token, peer)
        if not scope.startswith(f"org:{self.org}"):
            raise fail("NOT_FOUND", "scope outside this organisation")
        if on and not reason:
            raise fail("SCHEMA_INVALID", "a freeze requires a reason")
        self._authorize(p, "freeze", scope)
        self._journal({"kind": "freeze", "scope": scope, "on": bool(on), "actor": p.subject, "reason": reason,
                       "ticket": ticket, "expires_at": (self.clock() + ttl_s) if (on and ttl_s) else None})
        self.log.log("warn", "freeze", scope=scope, on=on, actor=p.subject, reason=reason)
        return {"scope": scope, "frozen": bool(on)}

    def transition(self, token: str, decision_id: str, to: str, reason: str, *, peer: str | None = None) -> dict:
        p = self._principal(token, peer)
        d = self.state["decisions"].get(decision_id)
        if d is None:
            raise fail("NOT_FOUND", "unknown decision")
        self._authorize(p, "lifecycle.transition", scope_of(self.org, d["tenant"], d["lattice"]))
        if to not in OPERATOR_TRANSITIONS or not legal(d["state"], to):
            raise fail("ILLEGAL_TRANSITION", f"{d['state']} -> {to} not permitted")
        entry = {"kind": "lifecycle", "decision_id": decision_id, "to": to, "actor": p.subject, "reason": reason}
        if to == "admitted":   # release from quarantine: requeue for delivery from the admission record
            rec = next(r for r in self.store.iter_all() if r["entry"].get("decision_id") == decision_id
                       and r["entry"]["kind"] == "admission")
            entry["requeue"] = {"lattice": d["lattice"], "manifest": rec["entry"]["manifest"], "attempts": 0,
                                "tenant": d["tenant"]}
        self._journal(entry)
        return {"decision_id": decision_id, "state": to}

    # ============================================================ read ops
    def inventory(self, token: str, tenant: str | None = None, lattice: str | None = None, *, peer=None) -> dict:
        p = self._principal(token, peer)
        self._authorize(p, "inventory.read", scope_of(self.org, tenant, lattice))
        out = {}
        for key, comps in self.state["inventory"].items():
            t, l = key.split("/", 1)
            if (tenant and t != tenant) or (lattice and l != lattice):
                continue
            out[key] = copy.deepcopy(comps)
        return {"schema": "PK_ECP_INVENTORY/1", "as_of_sequence": self.store.head_seq, "lattices": out}

    def _decision(self, decision_id: str) -> dict | None:
        d = self.state["decisions"].get(decision_id)
        if d is not None:
            return d
        for r in self.store.iter_all():                # pruned from memory: rebuild from the journal
            e = r["entry"]
            if e.get("decision_id") == decision_id and e["kind"] == "admission":
                d = {k: e[k] for k in ("decision_id", "request_id", "principal", "tenant", "lattice", "admitted",
                                       "errors", "manifest_sha256", "policy_version", "config_digest", "trace_id",
                                       "component_count")}
                d.update(sequence=r["sequence"], state="admitted" if e["admitted"] else "rejected", history=[])
            elif d is not None and e.get("decision_id") == decision_id and e["kind"] == "lifecycle":
                d["state"] = e["to"]
                d["history"].append({"state": e["to"], "sequence": r["sequence"]})
        return d

    def explain(self, token: str, decision_id: str, *, peer=None) -> dict:
        p = self._principal(token, peer)
        d = self._decision(decision_id)
        if d is None:
            raise fail("NOT_FOUND", "unknown decision")
        self._authorize(p, "decision.read", scope_of(self.org, d["tenant"], d["lattice"]))
        cfg = next((h for h in self.state["config"]["history"] if h["digest"] == d["config_digest"]), None)
        return {"schema": "PK_ECP_EXPLAIN/1", "decision": copy.deepcopy(d), "in_memory": decision_id in self.state["decisions"], "config": cfg,
                "scope": scope_of(self.org, d["tenant"], d["lattice"]),
                "frozen_by": self.frozen_by(scope_of(self.org, d["tenant"], d["lattice"])),
                "checks": ["authenticated principal", "schema PK_ECP_ADMIT/1", "freeze", "rbac:admit", "idempotency",
                           "quota", "limits", "registry", "signer+signature", "attestations", "policy-engine"]}

    def audit_query(self, token: str, *, after_sequence: int = 0, limit: int = 100, kind: str | None = None,
                    tenant: str | None = None, peer=None) -> dict:
        p = self._principal(token, peer)
        self._authorize(p, "audit.read", scope_of(self.org, tenant))
        limit = max(1, min(limit, 1000))
        out = []
        for r in self.store.iter_all():
            if r["sequence"] <= after_sequence:
                continue
            e = r["entry"]
            if kind and e["kind"] != kind:
                continue
            if tenant and e.get("tenant") != tenant:
                continue
            out.append(r)
            if len(out) >= limit:
                break
        return {"records": out, "next_after": out[-1]["sequence"] if out else after_sequence,
                "head": self.store.head_seq}

    def audit_export(self, token: str, *, peer=None) -> dict:
        """Immutable, MAC-sealed export of all retained records (SIEM/legal hold)."""
        p = self._principal(token, peer)
        self._authorize(p, "audit.export", scope_of(self.org))
        recs = list(self.store.iter_all())
        body = {"schema": "PK_ECP_EXPORT/1", "org": self.org, "exported_by": p.subject, "ts": self.clock(),
                "count": len(recs), "head": self.store.head_hash, "records_sha256": digest(recs)}
        self._journal({"kind": "maintenance", "action": "audit_export", "actor": p.subject, "count": len(recs)})
        return {"manifest": dict(body, mac=hmac_hex(self.store.anchor_key, EXPORT_DOMAIN, body)), "records": recs}

    # ======================================================= ops / health
    def is_leader(self) -> bool:
        lease = self.store.read_lease()
        return bool(lease and lease.holder == self.store.node_id and lease.epoch == self.store.epoch
                    and lease.expires_at > self.clock())

    def heartbeat(self) -> bool:
        try:
            self.store.acquire()
            return True
        except ControlPlaneError:
            return False

    def anchor(self) -> dict:
        a = self.store.anchor()
        self.metrics.set("inv66_audit_anchor_sequence", a["sequence"])
        return a

    def compact(self) -> dict:
        with self._lock:
            out = self.store.compact(self.snapshot_state())
            self.compaction_due.clear()
            self.metrics.inc("inv66_compactions")
            return out

    def run_maintenance(self) -> dict:
        """One ops-loop tick: renew lease, compact if due, anchor, purge idempotency, refresh gauges."""
        out = {"leader": self.heartbeat()}
        if out["leader"]:
            if self.compaction_due.is_set():
                out["compaction"] = self.compact()
            if self.store.head_seq and (not getattr(self, "_last_anchor", None) or self._last_anchor != self.store.head_seq):
                out["anchor"] = self.anchor()["sequence"]
                self._last_anchor = self.store.head_seq
        out["idempotency_purged"] = self.purge_idempotency()
        self.refresh_gauges()
        return out

    def start_background(self, interval_s: float = 1.0) -> threading.Event:
        stop = threading.Event()

        def loop():
            while not stop.wait(interval_s):
                try:
                    self.run_maintenance()
                except Exception as exc:          # never kill the loop; surface via logs/metrics
                    self.metrics.inc("inv66_maintenance_errors")
                    self.log.log("error", "maintenance_failed", error=str(exc))
        threading.Thread(target=loop, daemon=True, name="inv66-maintenance").start()
        return stop

    def purge_idempotency(self) -> int:
        with self._lock:
            ttl = self.policy.idempotency_ttl_s
            stale = [k for k, v in self.state["idem"].items() if self.clock() - v["ts"] > ttl]
            for k in stale:
                del self.state["idem"][k]
            return len(stale)

    def health(self) -> dict:
        ok_chain, detail = self.store.verify_all()
        return {"status": "ok" if ok_chain else "failed", "audit_chain": detail}

    def readiness(self) -> dict:
        ready = self.is_leader() and self.policy is not None and self.dependency_status["store"] == "ok"
        return {"ready": ready, "leader": self.is_leader(), "epoch": self.store.epoch,
                "freezes": {k: {kk: v[kk] for kk in ("reason", "ticket", "expires_at")} for k, v in self.state["freezes"].items()},
                "config": self.policy.version if self.policy else None,
                "dependencies": dict(self.dependency_status),
                "breakers": {b.name: b.state for b in (self.policy_breaker, self.deploy_breaker)}}

    def version_info(self) -> dict:
        return {"element": "INV-66", "version": __version__, "protocols": {"admit": list(ADMIT_PROTOCOLS),
                "rbac": ["PK_ECP_RBAC/1"], "audit": ["PK_ECP_AUDIT/1"], "config": ["PK_ECP_CONFIG/1"]},
                "config": self.policy.version, "config_digest": self.policy.digest,
                "audit_head": {"sequence": self.store.head_seq, "hash": self.store.head_hash},
                "capabilities": ["admit", "rbac", "audit", "inventory", "explain", "freeze", "lifecycle",
                                 "config-rollback", "anchoring", "gitops"]}

    def refresh_gauges(self) -> None:
        self.metrics.set("inv66_outbox_depth", len(self.state["outbox"]))
        self.metrics.set("inv66_inflight", self.bulkhead.inflight)
        self.metrics.set("inv66_audit_head_sequence", self.store.head_seq)
        self.metrics.set("inv66_freezes_active", len(self.state["freezes"]))
        self.metrics.set("inv66_leader", 1 if self.is_leader() else 0)
        for b in (self.policy_breaker, self.deploy_breaker):
            self.metrics.set("inv66_breaker_open", 1 if b.state == "open" else 0, dependency=b.name)
