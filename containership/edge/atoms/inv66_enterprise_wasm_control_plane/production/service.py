"""The INV-66 production control-plane service.

One pipeline for every admission (``PK_ECP_ADMIT/1``)::

    schema ─► authenticate ─► quarantine ─► RBAC(admit) ─► shed/quota ─► idempotency
          ─► manifest guardrails (4.2.0 engine) ─► provenance ─► org policy (local + GAP-13)
          ─► JOURNAL decision (fail closed) ─► lifecycle ─► deliver to INV-63 (retry/breaker)
          ─► JOURNAL delivery outcome

Invariants (tested in ``tests/``):

* **I1** nothing is delivered unless an ``admit.decision`` with ``admitted: true``
  is durably journaled first (SLO "zero unadmitted manifests forwarded");
* **I2** a journal failure means *no admission*: ``ECP_AUDIT_UNAVAILABLE`` is raised
  and nothing is delivered;
* **I3** all state (config generation, overlay bindings, freezes, lifecycle,
  inventory, idempotency) is a pure function of the journal: restart = replay;
* **I4** every refusal after authentication-parse is journaled (``admit.refused``)
  except load-shedding, which happens before any evaluation and is counted in
  ``ecp_shed_total`` instead.
"""
from __future__ import annotations

import copy
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from . import schema
from .adapters import DeploymentManager, InMemoryDeploymentManager
from .config import ConfigManager, Policy
from .errors import EcpError, reason
from .identity import Authenticator, Principal
from .journal import Journal
from .lifecycle import Lifecycle
from .policy_engine import ExternalPolicy, evaluate_local
from .provenance import RegistryResolver, verify_component
from .quarantine import QuarantineController
from .quota import Quotas
from .rbac import Binding, Rbac, parse_scope, scope_path
from .resilience import CircuitBreaker, Deadline, DependencyHealth, IdempotencyStore, LoadShedder, RetryPolicy
from .telemetry import Logger, Metrics, Tracer
from .util import canonical_json, digest_of, new_id, now, sha256_hex

VERSION = "4.3.0"
PROTOCOLS = ("PK_ECP_ADMIT/1", "PK_ECP_RBAC/1", "PK_ECP_AUDIT/1", "PK_ECP_AUDIT/2", "PK_ECP_ERROR/1",
             "PK_ECP_CONFIG/1", "PK_ECP_HEALTH/1", "PK_ECP_INVENTORY/1", "PK_ECP_DELIVER/1")
_ID_LIMIT = 256


def json_key(d: dict[str, Any]) -> str:
    return canonical_json(d).decode()


def _clean(value: Any, label: str, out: list[dict[str, Any]], limit: int = _ID_LIMIT) -> Optional[str]:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > limit \
            or any(ord(c) < 32 or ord(c) == 127 for c in value):
        out.append(reason("ECP_MANIFEST_INVALID", f"{label} must be a non-empty trimmed printable string "
                                                  f"of at most {limit} characters", field=label[:128]))
        return None
    return value


class ControlPlaneService:
    def __init__(self, root: Path, *, authenticator: Authenticator,
                 deployer: Optional[DeploymentManager] = None, external_policy: Optional[ExternalPolicy] = None,
                 resolver: Optional[RegistryResolver] = None, journal: Any = None, keyring=None,
                 clock: Callable[[], float] = now, logger: Optional[Logger] = None,
                 retry: Optional[RetryPolicy] = None, max_inflight: int = 256, per_tenant_inflight: int = 64,
                 segment_records: int = 10_000, fsync: bool = True, lease=None):
        self.root = Path(root)
        self.clock = clock
        self.journal = journal or Journal(self.root / "journal", keyring=keyring, clock=clock,
                                          segment_records=segment_records, fsync=fsync)
        self.lease = lease
        self.auth = authenticator
        self.deployer = deployer or InMemoryDeploymentManager()
        self.external_policy = external_policy
        self.resolver = resolver
        self.metrics = Metrics()
        self.tracer = Tracer()
        self.log = logger or Logger(stream=False)  # disabled unless a logger is supplied
        self.retry = retry or RetryPolicy(max_attempts=3, base_s=0.01, cap_s=0.2)
        self.delivery_breaker = CircuitBreaker("deployment", clock=clock)
        self.deps = DependencyHealth(clock=clock)
        for d, req in (("journal", True), ("deployment", False), ("policy", False), ("identity", True)):
            self.deps.register(d, req)
        self.shedder = LoadShedder(max_inflight, per_tenant_inflight)
        self.quotas = Quotas(clock=clock)
        self._lock = threading.RLock()
        self._key_locks = [threading.Lock() for _ in range(64)]  # striped idempotency locks
        self._describe_metrics()
        self._reset_state()
        self._replay()
        self.started_at = clock()

    # ================================================================ state
    def _reset_state(self) -> None:
        self.config = ConfigManager(self.journal)
        self.quarantine = QuarantineController()
        self.lifecycle = Lifecycle()
        self.idem = IdempotencyStore()
        self.inventory: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        self._inv_by_decision: dict[str, list[tuple[str, str, str, str]]] = {}
        self.decisions: dict[str, int] = {}  # decision_id -> journal seq
        self.pending: dict[str, dict[str, Any]] = {}  # decision_id -> delivery work item
        self.pending_bodies: dict[str, dict[str, Any]] = {}  # carried through checkpoints
        self.overlay: list[Binding] = []
        self.overlay_authority: dict[str, tuple[str, ...]] = {}  # binding -> broadest creator authority
        self.rbac_revision = 0  # journal seq of the last RBAC mutation (optimistic concurrency token)
        self._rbac_cache: Optional[tuple[str, int, Rbac]] = None

    def _replay(self) -> None:
        n = 0
        for kind, body, rec in self.journal.replay():
            self._apply(kind, body, rec)
            n += 1
        self.replayed = n
        self.deps.report("journal", True)

    def refresh(self) -> None:
        """Follower read path: rebuild from the (shared) journal."""
        with self._lock:
            if hasattr(self.journal, "reload_tail"):
                self.journal.reload_tail()
            self._reset_state()
            self._replay()

    def _apply(self, kind: str, body: dict[str, Any], rec: dict[str, Any]) -> None:
        if kind == "state.checkpoint":
            self.config.load_checkpoint(body["config"])
            self.overlay = [Binding.from_doc(b) for b in body["overlay"]]
            self.overlay_authority = {k: tuple(v.split("/")) for k, v in body.get("overlay_authority", {}).items()}
            self.rbac_revision = body.get("rbac_revision", 0)
            self.quarantine = QuarantineController()
            for scope, f in body["frozen"].items():
                self.quarantine.apply_record("quarantine.freeze", {"scope": scope, "by": f["by"],
                                                                   "reason": f.get("reason", ""), "seq": f.get("seq")})
            self.lifecycle = Lifecycle()
            for did, st in body["lifecycle"].items():
                self.lifecycle.apply(did, st)
            self.inventory = {(i["tenant"], i["lattice"], i["app"], i["component"]): dict(i) for i in body["inventory"]}
            self._inv_by_decision = {}
            for k, i in self.inventory.items():
                self._inv_by_decision.setdefault(i["decision_id"], []).append(k)
            self.pending = dict(body["pending"])
            self.pending_bodies = dict(body["pending_bodies"])
            self.decisions = {d: s for d, s in body["decisions"].items()}
            self._rbac_cache = None
            return
        if kind.startswith("config."):
            self.config.apply_record(kind, body, rec)
        elif kind.startswith("quarantine."):
            self.quarantine.apply_record(kind, {**body, "seq": rec["seq"]})
        elif kind == "rbac.bind":
            self.overlay.append(Binding.from_doc(body["binding"]))
            if body.get("authority"):
                bkey = json_key(body["binding"])
                prev = self.overlay_authority.get(bkey)
                new = tuple(body["authority"].split("/"))
                self.overlay_authority[bkey] = new if prev is None or len(new) < len(prev) else prev
            self.rbac_revision = rec["seq"]
        elif kind == "rbac.unbind":
            self.overlay_authority.pop(json_key(body["binding"]), None)
            self.rbac_revision = rec["seq"]
            b = Binding.from_doc(body["binding"])
            self.overlay = [x for x in self.overlay if x != b]
        elif kind == "admit.decision":
            did = body["decision_id"]
            self.decisions[did] = rec["seq"]
            if body.get("idempotency_key"):
                self.idem.put(body["idempotency_key"], body["request_digest"], self._public(body, rec["seq"]))
            if body.get("dry_run"):
                return
            state = "admitted" if body["admitted"] else "rejected"
            self.lifecycle.apply(did, state)
            if body["admitted"]:
                keys = self._inv_by_decision.setdefault(did, [])
                for c in body["manifest"]["components"]:
                    k = (body["tenant"], body["lattice"], body["app"], c["name"])
                    old = self.inventory.get(k)
                    if old is not None and old["decision_id"] != did:
                        old_keys = self._inv_by_decision.get(old["decision_id"], [])
                        if k in old_keys:
                            old_keys.remove(k)
                    keys.append(k)
                    self.inventory[k] = {
                        "tenant": body["tenant"], "lattice": body["lattice"], "app": body["app"],
                        "component": c["name"], "image": c["image"], "manifest_sha256": body["manifest_sha256"],
                        "state": state, "decision_id": did, "updated_seq": rec["seq"]}
        elif kind == "lifecycle.transition":
            did, to = body["decision_id"], body["to_state"]
            self.lifecycle.apply(did, to)
            if to == "delivery_pending":
                self.pending[did] = body.get("work") or self.pending.get(did, {})
            elif did in self.pending and to != "delivery_pending":
                self.pending.pop(did, None)
            for k in self._inv_by_decision.get(did, ()):
                item = self.inventory[k]
                item["state"], item["updated_seq"] = to, rec["seq"]

    def _rbac(self, policy: Policy) -> Rbac:
        key = (policy.generation, len(self.overlay))
        if self._rbac_cache and self._rbac_cache[:2] == key:
            return self._rbac_cache[2]
        rb = Rbac(policy.doc["roles"], list(policy.rbac.bindings) + self.overlay)
        self._rbac_cache = (*key, rb)
        return rb

    def _policy(self) -> Policy:
        p = self.config.active
        if p is None:
            raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "no active configuration generation", dependency="config")
        return p

    def _append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            rec = self.journal.append(kind, body)
        except EcpError as e:
            if e.code == "ECP_AUDIT_UNAVAILABLE":
                self.deps.report("journal", False, "append failed")
                self.metrics.inc("ecp_audit_append_failures_total")
            raise
        self.deps.report("journal", True)
        self.metrics.inc("ecp_audit_entries_total", kind=kind)
        return rec

    # ================================================================ identity
    def principal(self, credential: Any = None, peer: Optional[str] = None) -> Principal:
        try:
            if isinstance(credential, Principal):
                return credential
            if credential is not None:
                return self.auth.authenticate_token(credential)
            if peer is not None:
                return self.auth.authenticate_peer(peer)
        except EcpError:
            self.metrics.inc("ecp_authn_failures_total")
            raise
        self.metrics.inc("ecp_authn_failures_total")
        raise EcpError("ECP_UNAUTHENTICATED", "no credential presented", reason="missing")

    # ================================================================ admission
    def _describe_metrics(self) -> None:
        m = self.metrics
        m.describe("ecp_admissions_total", "counter", "Admission decisions by outcome")
        m.describe("ecp_rbac_denials_total", "counter", "Admissions refused by RBAC")
        m.describe("ecp_audit_entries_total", "counter", "Journal records appended by kind")
        m.describe("ecp_admission_latency_ms", "histogram", "Admission decision latency (ms)")
        m.describe("ecp_shed_total", "counter", "Requests shed before evaluation")
        m.describe("ecp_quota_exceeded_total", "counter", "Requests refused by tenant quota")
        m.describe("ecp_delivery_total", "counter", "Deliveries to the deployment manager by outcome")
        m.describe("ecp_authn_failures_total", "counter", "Rejected credentials")
        m.describe("ecp_inflight", "gauge", "Admissions in flight")

    def admit(self, request: dict[str, Any], credential: Any = None, *, peer: Optional[str] = None,
              deliver: bool = True) -> dict[str, Any]:
        t0 = time.perf_counter()
        schema.validate(request, "PK_ECP_ADMIT_REQUEST_1")
        tenant, lattice = request["tenant"], request["lattice"]
        with self.tracer.span("ecp.admit", request.get("traceparent"), tenant=tenant, lattice=lattice) as span:
            deadline = Deadline(request.get("deadline_ms") or self._policy().limits["default_deadline_ms"])
            try:
                self.shedder.acquire(tenant)
            except EcpError:
                self.metrics.inc("ecp_shed_total", tenant=tenant)
                raise
            self.metrics.set("ecp_inflight", self.shedder.inflight)
            try:
                return self._admit(request, credential, peer, deliver, deadline, span, t0)
            finally:
                self.shedder.release(tenant)
                self.metrics.set("ecp_inflight", self.shedder.inflight)

    def _refuse(self, err: EcpError, request: dict[str, Any], principal: Optional[Principal], span) -> None:
        body = {"request_id": request["request_id"], "tenant": request["tenant"], "lattice": request["lattice"],
                "code": err.code, "principal": principal.ref() if principal else None, "trace_id": span.trace_id,
                "config_generation": self.config.active.generation if self.config.active else None}
        try:
            self._append("admit.refused", body)
        except EcpError:
            pass  # the refusal still stands; journal outage is already surfaced via health
        self.metrics.inc("ecp_admissions_total", outcome="refused", code=err.code)
        self.log.log("warning", "admit.refused", request_id=request["request_id"], tenant=request["tenant"],
                     lattice=request["lattice"], codes=[err.code], trace_id=span.trace_id)

    def _admit(self, request, credential, peer, deliver, deadline: Deadline, span, t0) -> dict[str, Any]:
        policy = self._policy()
        tenant, lattice = request["tenant"], request["lattice"]
        principal: Optional[Principal] = None
        try:
            self.deps.require("identity")
            principal = self.principal(credential, peer)
            target = scope_path(principal.org, tenant, lattice)
            if target[0] != policy.doc["org"]:
                raise EcpError("ECP_FORBIDDEN", "principal organisation not served here", scope=target[0])
            self.quarantine.check(target)
            cap = "admit.dry_run" if request.get("dry_run") else "admit"
            try:
                self._rbac(policy).check(principal, cap, target)
            except EcpError:
                self.metrics.inc("ecp_rbac_denials_total")
                raise
            try:
                self.quotas.take(policy.doc["quotas"], tenant)
            except EcpError:
                self.metrics.inc("ecp_quota_exceeded_total", tenant=tenant)
                raise
        except EcpError as e:
            if e.spec.category in ("auth", "policy", "resource", "security"):
                self._refuse(e, request, principal, span)
            raise

        req_digest = digest_of({k: v for k, v in request.items() if k not in ("traceparent", "deadline_ms")})
        ikey = request.get("idempotency_key")
        if ikey:  # keys are scoped to the authenticated principal (review finding R3)
            ikey = f"{principal.issuer}|{principal.subject}|{ikey}"
        if not ikey:
            return self._decide(policy, request, principal, target, req_digest, None, deliver, deadline, span, t0)
        with self._key_locks[hash(ikey) % len(self._key_locks)]:  # one evaluation per key, even under races
            prior = self.idem.get(ikey, req_digest)
            if prior is not None:
                return {**copy.deepcopy(prior), "idempotent_replay": True}
            return self._decide(policy, request, principal, target, req_digest, ikey, deliver, deadline, span, t0)

    def _decide(self, policy, request, principal, target, req_digest, ikey, deliver, deadline, span, t0):
        tenant, lattice = request["tenant"], request["lattice"]

        deadline.check("before evaluation")
        manifest = request["manifest"]
        reasons, evidence = self._evaluate(policy, manifest, target, request)
        deadline.check("before journal")
        admitted = not reasons
        did = new_id("dec-")
        app = manifest.get("app") or (manifest["components"][0].get("name") if manifest.get("components") else "app")
        body = {"decision_id": did, "request_id": request["request_id"], "idempotency_key": ikey,
                "request_digest": req_digest, "tenant": tenant, "lattice": lattice, "org": target[0], "app": app,
                "principal": principal.ref(), "admitted": admitted, "reasons": reasons,
                "manifest_sha256": evidence["manifest_sha256"], "config_generation": policy.generation,
                "evidence": evidence, "dry_run": bool(request.get("dry_run")), "trace_id": span.trace_id,
                "source": manifest.get("source"), "manifest": manifest if admitted else None}
        with self._lock:
            rec = self._append("admit.decision", body)  # I1/I2: durable before visible, raises on failure
            self._apply("admit.decision", body, rec)
        latency = (time.perf_counter() - t0) * 1000
        self.metrics.observe("ecp_admission_latency_ms", latency)
        self.metrics.inc("ecp_admissions_total", outcome="admitted" if admitted else "rejected")
        self.log.log("info", "admit.decision", request_id=request["request_id"], decision_id=did, tenant=tenant,
                     lattice=lattice, admitted=admitted, codes=[r["code"] for r in reasons], latency_ms=round(latency, 3),
                     trace_id=span.trace_id, span_id=span.span_id, generation=policy.generation[:16],
                     subject=principal.subject)
        decision = self._public(body, rec["seq"], latency)
        if admitted and not request.get("dry_run") and deliver:
            decision["state"] = self._deliver(did, body, deadline)
        return decision

    def _public(self, body: dict[str, Any], seq: int, latency: float = 0.0) -> dict[str, Any]:
        state = "dry_run" if body.get("dry_run") else ("admitted" if body["admitted"] else "rejected")
        return {"protocol": "PK_ECP_ADMIT/1", "request_id": body["request_id"], "decision_id": body["decision_id"],
                "admitted": body["admitted"], "state": state, "tenant": body["tenant"], "lattice": body["lattice"],
                "principal": body["principal"], "reasons": body["reasons"],
                "manifest_sha256": body["manifest_sha256"], "config_generation": body["config_generation"],
                "audit_seq": seq, "trace_id": body["trace_id"], "latency_ms": round(latency, 3),
                "idempotent_replay": False}

    def _evaluate(self, policy: Policy, manifest: dict[str, Any], target, request) -> tuple[list, dict]:
        """The 4.2.0 guardrails, now with typed reasons, plus provenance and org policy."""
        out: list[dict[str, Any]] = []
        lim = policy.limits
        try:
            encoded = canonical_json(manifest)
            mdigest, size = sha256_hex(encoded), len(encoded)
        except (TypeError, ValueError, OverflowError):
            out.append(reason("ECP_MANIFEST_INVALID", "manifest must be finite canonical JSON"))
            mdigest, size = None, None
        if size is not None and size > lim["max_manifest_bytes"]:
            out.append(reason("ECP_RESOURCE_LIMIT", "manifest exceeds byte limit", limit=lim["max_manifest_bytes"],
                              observed=size))
        comps = manifest.get("components") or []
        if len(comps) > lim["max_components"]:
            out.append(reason("ECP_RESOURCE_LIMIT", "too many components", limit=lim["max_components"],
                              observed=len(comps)))
        seen: set[str] = set()
        prov: list[dict[str, Any]] = []
        t = self.clock()
        for i, c in enumerate(comps[: lim["max_components"]]):
            label = f"component[{i}]"
            name = _clean(c.get("name"), f"{label}.name", out)
            if name:
                label = name
                if name in seen:
                    out.append(reason("ECP_MANIFEST_INVALID", f"{name}: duplicate component name", component=name))
                seen.add(name)
            image = c.get("image")
            if isinstance(image, str) and "/" in image:
                reg = image.split("/", 1)[0].lower()
                if not policy.registry_allowed(reg, target):
                    out.append(reason("ECP_REGISTRY_NOT_APPROVED", f"{label}: registry {reg} not approved",
                                      component=label, registry=reg, scope="/".join(target)))
            else:
                out.append(reason("ECP_MANIFEST_INVALID", f"{label}: malformed image reference", component=label))
            r, ev = verify_component(policy, c, target, t, label, self.resolver)
            out.extend(r)
            prov.append(ev)
        ctx = {"tenant": target[1], "lattice": target[2], "environment": policy.environment}
        local = evaluate_local(policy.doc["policy"]["rules"], ctx, comps)
        for f in local["fired"]:
            out.append(reason("ECP_POLICY_DENIED", f"{f['rule']}: {f['message']}", rule=f["rule"]))
        external = None
        if policy.doc["policy"]["engine"] == "external" and self.external_policy is not None:
            external = self.external_policy.evaluate(
                {"tenant": target[1], "lattice": target[2], "org": target[0], "manifest_sha256": mdigest,
                 "components": [{"name": c.get("name"), "image": c.get("image")} for c in comps]},
                headers=self.tracer.headers())
            self.deps.report("policy", external.get("source") in ("live",), external.get("source"))
            if not external["allow"]:
                out.extend(external["reasons"] or [reason("ECP_POLICY_DENIED", "external policy denied")])
        elif policy.doc["policy"]["engine"] == "external":
            out.append(reason("ECP_DEPENDENCY_UNAVAILABLE", "external policy engine not wired; fail closed",
                              dependency="policy"))
        return out, {"manifest_sha256": mdigest, "manifest_bytes": size, "component_count": len(comps),
                     "provenance": prov, "policy_local": local, "policy_external": external}

    # ================================================================ delivery
    def _transition(self, did: str, to: str, **extra: Any) -> None:
        self.lifecycle.check(did, to)
        body = {"decision_id": did, "to_state": to, **extra}
        with self._lock:
            rec = self._append("lifecycle.transition", body)
            self._apply("lifecycle.transition", body, rec)

    def _deliver(self, did: str, body: dict[str, Any], deadline: Optional[Deadline] = None) -> str:
        work = {"tenant": body["tenant"], "lattice": body["lattice"], "app": body["app"],
                "manifest_sha256": body["manifest_sha256"], "audit_seq": self.decisions[did]}
        if self.lifecycle.get(did) != "delivery_pending":
            self._transition(did, "delivery_pending", work=work)
        payload = {"decision_id": did, "manifest_sha256": body["manifest_sha256"], "manifest": body["manifest"],
                   "audit_seq": work["audit_seq"]}
        timeout = min(2.0, deadline.remaining()) if deadline else 2.0
        try:
            ack = self.retry.run(lambda: self.delivery_breaker.call(
                lambda: self.deployer.deliver(body["tenant"], body["lattice"], body["app"], payload,
                                              self.tracer.headers(), max(0.05, timeout))), deadline)
        except EcpError as e:
            self.deps.report("deployment", not e.spec.retryable, e.code)
            if e.spec.retryable:
                self.metrics.inc("ecp_delivery_total", outcome="pending")
                return "delivery_pending"
            self._transition(did, "rejected", code=e.code)
            self.metrics.inc("ecp_delivery_total", outcome="refused")
            return "rejected"
        self.deps.report("deployment", True)
        self._transition(did, "delivered", revision=ack.get("revision", ""))
        self.metrics.inc("ecp_delivery_total", outcome="delivered")
        return "delivered"

    def _decision_body(self, did: str) -> Optional[dict[str, Any]]:
        seq = self.decisions.get(did)
        if seq is not None:
            rec = next(self.journal.records(seq, seq), None)
            if rec is not None:
                return self.journal.body(rec)
        return self.pending_bodies.get(did)

    def redeliver_pending(self) -> dict[str, str]:
        """Resume deliveries left pending by a crash or an outage (idempotent on decision id)."""
        out = {}
        for did in list(self.pending):
            body = self._decision_body(did)
            if body is None:
                raise EcpError("ECP_STORE_CORRUPT", "pending decision body missing", request_id=did[:128])
            out[did] = self._deliver(did, body)
        return out

    def checkpoint(self) -> dict[str, Any]:
        """Append a full state checkpoint so older segments can be compacted without losing state."""
        with self._lock:
            live = {d for d, st in self.lifecycle.state.items() if st not in ("rejected", "retired")}
            body = {"config": self.config.checkpoint(), "overlay": [b.to_doc() for b in self.overlay],
                    "rbac_revision": self.rbac_revision,
                    "overlay_authority": {k: "/".join(v) for k, v in self.overlay_authority.items()},
                    "frozen": self.quarantine.snapshot(),
                    "lifecycle": {d: st for d, st in self.lifecycle.state.items() if d in live},
                    "inventory": [dict(v) for v in self.inventory.values()],
                    "pending": dict(self.pending),
                    "pending_bodies": {d: self._decision_body(d) for d in self.pending},
                    "decisions": {d: s for d, s in self.decisions.items() if d in live}}
            rec = self._append("state.checkpoint", body)
            return {"seq": rec["seq"], "bytes": len(canonical_json(body))}

    # ================================================================ administration
    def stage_config(self, doc, principal: Principal, *, source_repo: str, source_rev: str, ticket: str = "") -> str:
        cur = self.config.active
        if cur is not None:
            self._rbac(cur).check(principal, "policy.admin", (cur.doc["org"],))
        return self.config.stage(doc, author=principal.subject, source_repo=source_repo, source_rev=source_rev,
                                 change_ticket=ticket)

    def approve_config(self, gen: str, principal: Principal) -> int:
        cur = self._policy()
        self._rbac(cur).check(principal, "config.approve", (cur.doc["org"],))
        return self.config.approve(gen, principal.subject)

    def activate_config(self, gen: str, principal: Optional[Principal], *, expected_active: Optional[str],
                        reason_: str = "", bootstrap: bool = False) -> Policy:
        cur = self.config.active
        if cur is not None:
            if principal is None:  # only the empty-store bootstrap may activate without a principal
                raise EcpError("ECP_UNAUTHENTICATED", "activation requires an authenticated principal")
            self._rbac(cur).check(principal, "config.activate", (cur.doc["org"],))
        who = principal.subject if principal else "bootstrap"
        p = self.config.activate(gen, activated_by=who, expected_active=expected_active, reason=reason_,
                                 bootstrap=bootstrap)
        self._rbac_cache = None
        self.log.log("info", "config.activated", generation=gen[:16], subject=who)
        return p

    def rollback_config(self, gen: str, principal: Principal, why: str) -> Policy:
        cur = self._policy()
        self._rbac(cur).check(principal, "config.activate", (cur.doc["org"],))
        p = self.config.rollback(gen, activated_by=principal.subject, reason=why)
        self._rbac_cache = None
        return p

    def rbac(self, request: dict[str, Any], principal: Principal) -> dict[str, Any]:
        schema.validate(request, "PK_ECP_RBAC_REQUEST_1")
        policy = self._policy()
        rb = self._rbac(policy)
        op = request["op"]
        if op in ("bind", "unbind"):
            b = Binding.from_doc(request["binding"])
            rb.check_delegation(principal, b)
            authority = rb.admin_authority(principal, b.scope)
            if op == "unbind":
                owner = self.overlay_authority.get(json_key(b.to_doc()))
                if b not in self.overlay:
                    raise EcpError("ECP_NOT_FOUND", "binding is not an overlay binding (config bindings change "
                                                    "only through a new config generation)", scope="/".join(b.scope))
                # the remover's authority must be at least as broad as the creator's (review finding R2)
                if owner is not None and len(authority) > len(owner):
                    raise EcpError("ECP_FORBIDDEN", "binding was created with broader authority than yours",
                                   capability="rbac.admin", scope="/".join(owner))
            if "if_revision" in request and request["if_revision"] != self.rbac_revision:
                raise EcpError("ECP_CONFIG_CONFLICT", "RBAC changed since if_revision", generation=str(self.rbac_revision))
            if b.role not in rb.roles:
                raise EcpError("ECP_CONFIG_INVALID", "unknown role", rule=b.role)
            with self._lock:
                body = {"binding": b.to_doc(), "by": principal.subject, "request_id": request["request_id"],
                        "reason": request.get("reason", "")[:256], "authority": "/".join(authority)}
                rec = self._append(f"rbac.{op}", body)
                self._apply(f"rbac.{op}", body, rec)
                self._rbac_cache = None
            return {"protocol": "PK_ECP_RBAC/1", "request_id": request["request_id"], "ok": True, "audit_seq": rec["seq"]}
        if op == "list":
            scope = parse_scope(request.get("scope") or policy.doc["org"])
            rb.check(principal, "rbac.admin", scope)
            items = [b.to_doc() for b in rb.bindings if b.scope[: len(scope)] == scope]
            return {"protocol": "PK_ECP_RBAC/1", "request_id": request["request_id"], "bindings": items,
                    "revision": self.rbac_revision}
        scope = parse_scope(request["scope"])
        rb.check(principal, "rbac.admin", scope)
        subj = Principal(subject=request["subject"], kind="user", issuer="check", org=scope[0])
        return {"protocol": "PK_ECP_RBAC/1", "request_id": request["request_id"],
                **rb.explain(subj, request["capability"], scope)}

    def freeze(self, scope: str, principal: Principal, why: str) -> dict[str, Any]:
        sc = parse_scope(scope)
        self._rbac(self._policy()).check(principal, "quarantine", sc)
        body = {"scope": scope, "by": principal.subject, "reason": why[:256]}
        with self._lock:
            rec = self._append("quarantine.freeze", body)
            self.quarantine.apply_record("quarantine.freeze", {**body, "seq": rec["seq"]})
        self.log.log("warning", "quarantine.freeze", scope=scope, subject=principal.subject, seq=rec["seq"])
        return {"frozen": scope, "audit_seq": rec["seq"]}

    def release(self, scope: str, principal: Principal, why: str) -> dict[str, Any]:
        sc = parse_scope(scope)
        policy = self._policy()
        self._rbac(policy).check(principal, "quarantine", sc)
        if sc not in self.quarantine.frozen:
            raise EcpError("ECP_NOT_FOUND", "scope is not frozen", scope=scope)
        need = int(policy.doc.get("dual_authorization", {}).get("quarantine_release", 2))
        body = {"scope": scope, "by": principal.subject, "reason": why[:256]}
        with self._lock:
            self._append("quarantine.release_vote", body)
            self.quarantine.apply_record("quarantine.release_vote", body)
            votes = self.quarantine.votes(sc)
            if len(votes) < need:
                return {"released": False, "votes": len(votes), "required": need}
            rec = self._append("quarantine.release", {**body, "approvers": sorted(votes)})
            self.quarantine.apply_record("quarantine.release", body)
        return {"released": True, "votes": len(votes), "required": need, "audit_seq": rec["seq"]}

    def emergency_disable(self, principal: Principal, why: str) -> dict[str, Any]:
        return self.freeze(self._policy().doc["org"], principal, f"EMERGENCY: {why}")

    def rollback_app(self, decision_id: str, principal: Principal, why: str) -> dict[str, Any]:
        seq = self.decisions.get(decision_id)
        if seq is None:
            raise EcpError("ECP_NOT_FOUND", "unknown decision", request_id=decision_id[:128])
        body = self.journal.body(next(self.journal.records(seq, seq)))
        self._rbac(self._policy()).check(principal, "quarantine", (body["org"], body["tenant"], body["lattice"]))
        self._transition(decision_id, "rolled_back", by=principal.subject, reason=why[:256])
        return {"decision_id": decision_id, "state": "rolled_back"}

    # ================================================================ read paths
    def explain(self, decision_id: str, principal: Principal) -> dict[str, Any]:
        """MC-053: link a decision to principal, policy generation, provenance, rules and audit position."""
        seq = self.decisions.get(decision_id)
        if seq is None:
            raise EcpError("ECP_NOT_FOUND", "unknown decision", request_id=decision_id[:128])
        rec = next(self.journal.records(seq, seq))
        body = self.journal.body(rec)
        target = (body["org"], body["tenant"], body["lattice"])
        self._rbac(self._policy()).check(principal, "explain.read", target)
        gen = body["config_generation"]
        hist = [h for h in self.config.history() if h["generation"] == gen]
        return {"schema": "PK_ECP_EXPLAIN/1", "decision_id": decision_id, "admitted": body["admitted"],
                "state": self.lifecycle.get(decision_id), "principal": body["principal"],
                "target": "/".join(target), "reasons": body["reasons"],
                "config": {"generation": gen, "activation": hist[-1] if hist else None},
                "provenance": body["evidence"]["provenance"], "policy_local": body["evidence"]["policy_local"],
                "policy_external": body["evidence"]["policy_external"],
                "manifest_sha256": body["manifest_sha256"], "source": body.get("source"),
                "audit": {"seq": rec["seq"], "hash": rec["hash"], "prev": rec["prev"]},
                "trace_id": body["trace_id"],
                "constraints": {"limits": self._policy().limits, "precedence": "security>residency>availability>slo>cost"}}

    @staticmethod
    def _read_scope(org: str, tenant: Optional[str], lattice: Optional[str]) -> tuple[str, ...]:
        if lattice is not None and tenant is None:
            raise EcpError("ECP_SCHEMA_INVALID", "lattice filter requires tenant", field="lattice")
        return scope_path(org, tenant, lattice)

    def inventory_view(self, principal: Principal, tenant: Optional[str] = None,
                       lattice: Optional[str] = None, *, cursor: int = 0, limit: int = 1000) -> dict[str, Any]:
        org = self._policy().doc["org"]
        self._rbac(self._policy()).check(principal, "inventory.read", self._read_scope(org, tenant, lattice))
        items = [dict(v) for v in self.inventory.values()
                 if (tenant is None or v["tenant"] == tenant) and (lattice is None or v["lattice"] == lattice)]
        items.sort(key=lambda x: (x["tenant"], x["lattice"], x["app"], x["component"]))
        limit = max(1, min(int(limit), 10_000))
        page = items[cursor: cursor + limit]
        out = {"schema": "PK_ECP_INVENTORY/1", "items": page, "as_of_seq": self.journal.head[0]}
        if cursor + limit < len(items):
            out["next_cursor"] = cursor + limit
        return out

    def audit_query(self, request: dict[str, Any], principal: Principal) -> dict[str, Any]:
        schema.validate(request, "PK_ECP_AUDIT_QUERY_1")
        org = self._policy().doc["org"]
        self._rbac(self._policy()).check(principal, "audit.read",
                                         self._read_scope(org, request.get("tenant"), request.get("lattice")))
        limit = request.get("limit", 1000)
        rows = self.journal.query(kind=request.get("kind"), tenant=request.get("tenant"),
                                  lattice=request.get("lattice"), outcome=request.get("outcome"),
                                  from_seq=request.get("from_seq", 1), to_seq=request.get("to_seq"),
                                  limit=limit, from_ts=request.get("from_ts"), to_ts=request.get("to_ts"),
                                  subject=request.get("subject"), request_id=request.get("request_ref"),
                                  decision_id=request.get("decision_id"))
        for r in rows:  # never return sealed manifests through the query API
            r["body"] = {k: v for k, v in r["body"].items() if k != "manifest"}
        out = {"protocol": "PK_ECP_AUDIT/1", "request_id": request["request_id"], "records": rows}
        if len(rows) >= limit:
            out["next_from_seq"] = rows[-1]["seq"] + 1  # stable cursor: sequence numbers never change
        return out

    def policy_impact(self, doc: dict[str, Any], principal: Principal) -> dict[str, Any]:
        """MC-026-T07 dry run: which live inventory entries would a proposed generation reject?"""
        from .config import build_policy
        cur = self._policy()
        self._rbac(cur).check(principal, "policy.admin", (cur.doc["org"],))
        proposed = build_policy(doc)
        t = self.clock()
        hits = []
        for item in self.inventory.values():
            if item["state"] in ("rejected", "retired", "rolled_back"):
                continue
            target = (proposed.doc["org"], item["tenant"], item["lattice"])
            reg = item["image"].split("/", 1)[0].lower()
            why = []
            if not proposed.registry_allowed(reg, target):
                why.append("ECP_REGISTRY_NOT_APPROVED")
            body = self._decision_body(item["decision_id"]) or {}
            comp = next((c for c in (body.get("manifest") or {}).get("components", [])
                         if c["name"] == item["component"]), None)
            if comp is not None:
                r, _ = verify_component(proposed, comp, target, t, item["component"], None)
                why += [x["code"] for x in r]
            if why:
                hits.append({**{k: item[k] for k in ("tenant", "lattice", "app", "component", "image", "decision_id")},
                             "codes": sorted(set(why))})
        return {"schema": "PK_ECP_POLICY_IMPACT/1", "proposed_generation": proposed.generation,
                "active_generation": cur.generation, "violations": hits, "checked": len(self.inventory)}

    def verify_audit_background(self, trusted_keys: Optional[dict[str, str]] = None) -> dict[str, Any]:
        """MC-035-T06: periodic verification; failures raise the alerting metric and a log event."""
        try:
            res = self.journal.verify(trusted_keys)
            self.metrics.set("ecp_audit_verified_head_seq", res["head_seq"])
            self.metrics.set("ecp_audit_last_verify_ok", 1)
            return res
        except EcpError as e:
            self.metrics.inc("ecp_audit_verify_failures_total")
            self.metrics.set("ecp_audit_last_verify_ok", 0)
            self.log.log("error", "audit.verify_failed", error=e.code)
            raise

    def audit_export(self, principal: Principal, from_seq: int = 1, to_seq: Optional[int] = None) -> dict[str, Any]:
        org = self._policy().doc["org"]
        self._rbac(self._policy()).check(principal, "audit.export", (org,))
        self._append("audit.export", {"by": principal.subject, "from_seq": from_seq, "to_seq": to_seq})
        return self.journal.export(from_seq, to_seq)

    def health(self) -> dict[str, Any]:
        """MC-049: liveness/readiness/version/config/dependency view (PK_ECP_HEALTH/1)."""
        p = self.config.active
        mode = "frozen" if p and self.quarantine.blocking((p.doc["org"],)) else self.deps.mode()
        role = "standalone"
        epoch = 0
        if self.lease is not None:
            st = self.lease.status()
            role, epoch = st["role"], st["epoch"]
        ready = p is not None and self.deps.mode() == "normal" and role in ("leader", "standalone")
        status = "ok" if ready and mode == "normal" else ("degraded" if p is not None else "failing")
        self._runtime_gauges()
        return {"schema": "PK_ECP_HEALTH/1", "status": status, "ready": ready, "version": VERSION,
                "site": p.doc["site"] if p else None, "started_at": self.started_at,
                "emergency": self.quarantine.snapshot(),
                "protocols": list(PROTOCOLS), "config_generation": p.generation if p else None, "role": role,
                "epoch": epoch, "journal_head": self.journal.head[0], "dependencies": self.deps.snapshot(),
                "mode": mode, "capabilities": sorted({"admit", "rbac", "audit.query", "audit.export", "inventory",
                                                      "explain", "quarantine", "config.generations"})}

    def _runtime_gauges(self) -> None:
        """MC-050-T04 process/runtime metrics (Linux /proc when available)."""
        import os as _os
        import resource as _res
        import threading as _th
        m = self.metrics
        m.set("process_max_rss_kb", _res.getrusage(_res.RUSAGE_SELF).ru_maxrss)
        m.set("process_threads", _th.active_count())
        try:
            m.set("process_open_fds", len(_os.listdir("/proc/self/fd")))
        except OSError:
            pass
        m.set("ecp_journal_head_seq", self.journal.head[0])
        m.set("ecp_delivery_pending", len(self.pending))
        m.set("ecp_idempotency_entries", len(self.idem))
        m.set("ecp_inventory_entries", len(self.inventory))
        m.set("ecp_breaker_open", 1 if self.delivery_breaker.state == "open" else 0, dependency="deployment")
        m.set("ecp_frozen_scopes", len(self.quarantine.frozen))

    def enforce_retention(self, archive=None) -> dict[str, Any]:
        """MC-046: drop journal segments older than ``retention_days`` (holds respected)."""
        days = self._policy().limits["retention_days"]
        cutoff = self.clock() - days * 86400
        keep_after = 0
        for rec in self.journal.records():
            if rec["ts"] < cutoff:
                keep_after = rec["seq"]
            else:
                break
        if keep_after == 0:
            return {"dropped_segments": 0, "summaries": []}
        cp = self.checkpoint()
        res = self.journal.compact(min(keep_after, cp["seq"] - 1), archive)
        res["checkpoint_seq"] = cp["seq"]
        return res
