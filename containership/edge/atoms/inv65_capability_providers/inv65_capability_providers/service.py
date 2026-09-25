"""ProviderService -- the production composition of every INV-65 runtime layer.

Order of checks on a call (each fails closed, each is audited on deny):
  authenticate (M07) -> validate call metadata (M14) -> lifecycle serving (M11)
  -> authorize decision (M08) -> link lookup by FULL identity scope (M06)
  -> admission/quotas (M15) -> idempotency (M14) -> circuit breaker (M15)
  -> resolve secret ref in caller scope (M09) -> bounded dispatch with deadline
  (M14) -> telemetry (M21).
Link mutations additionally pass residency (M40), quotas, the config history
(M10), the fenced lease (M17) and the durable store (M05) before they are acked.
Backends implement ``fixtures.providers.base.Backend``; INV-65 never
implements a real backing service.
"""
from __future__ import annotations

import json
import time
import zlib

from .audit.emitter import AuditLog
from .authn.authenticator import Authenticator
from .authz.decision import AuthorizationEnforcer
from .config.model import ConfigHistory
from .errors.mapping import ProviderFault, new_correlation_id, to_envelope
from .health.model import HealthModel
from .identity.context import IdentityContext
from .lifecycle.state_machines import SERVING_PROVIDER, link_machine, provider_machine
from .observability.telemetry import JsonLogger, Metrics, Tracer, explain, parse_traceparent
from .provider import _validate_identifier, _validated_config
from .residency.engine import ResidencyEngine
from .resilience.failover import degraded_allows
from .resilience.fencing import LeaseManager
from .runtime.admission import AdmissionController
from .runtime.call_control import CancelToken, Deadline, Dispatcher, call_with_retry
from .runtime.circuit_breaker import CircuitBreaker
from .runtime.idempotency import IdempotencyCache
from .runtime.quotas import LinkQuotas
from .schemas import SchemaError, check
from .secret_refs.resolver import SecretResolver
from .state.store import LinkStateStore


def _ms_since(t0: float) -> float:
    return time.perf_counter() - t0


class ProviderService:
    def __init__(self, *, contract_id: str, backend, store: LinkStateStore, authenticator: Authenticator,
                 authz: AuthorizationEnforcer, secrets: SecretResolver, residency: ResidencyEngine,
                 instance_id: str, site: str, region: str, environment: str,
                 leases: LeaseManager | None = None, audit: AuditLog | None = None,
                 admission: AdmissionController | None = None, quotas: LinkQuotas | None = None,
                 dispatcher: Dispatcher | None = None):
        self.contract_id = _validate_identifier(contract_id, "contract id")
        self.backend, self.store, self.authn, self.authz = backend, store, authenticator, authz
        self.secrets, self.residency = secrets, residency
        self.instance_id, self.site, self.region, self.environment = instance_id, site, region, environment
        self.leases = leases or LeaseManager()
        self.audit = audit or AuditLog()
        self.admission = admission or AdmissionController()
        self.quotas = quotas or LinkQuotas()
        self.dispatcher = dispatcher or Dispatcher()
        self.breaker = CircuitBreaker()
        self.idem = IdempotencyCache()
        self.history = ConfigHistory()
        self.metrics, self.log, self.tracer = Metrics(), JsonLogger(), Tracer()
        self.health_model = HealthModel(contract_id)
        self.lifecycle = provider_machine()
        self.link_states: dict[tuple, object] = {}
        self.slot = f"{contract_id}|{site}|{environment}"
        self.epoch = 0
        self.degraded_ops = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> int:
        self.epoch = self.leases.acquire(self.slot, self.instance_id)
        restored = 0
        for key, rec in self.store.items():
            m = link_machine()
            m.to("active", "restored")
            self.link_states[tuple(key)] = m
            restored += 1
        self.health_model.set_dependency("backend", "ok" if self.backend.healthy() else "down")
        self.health_model.set_dependency("state_store", "ok")
        self.lifecycle.to("ready", f"restored {restored} links")
        self.audit.emit("provider.start", "ok", self.instance_id, self.slot, f"epoch={self.epoch} restored={restored}")
        self.metrics.gauge("pk_links", restored, {"contract": self.contract_id})
        return restored

    def _fenced(self) -> None:
        self.leases.validate(self.slot, self.instance_id, self.epoch)

    def drain(self, reason: str = "operator drain") -> None:
        self.lifecycle.to("draining", reason)
        self.audit.emit("provider.drain", "ok", self.instance_id, self.slot, reason)

    def disable(self, approvers: list, reason: str) -> None:
        from .rollout.controller import emergency_disable_authorized
        emergency_disable_authorized(approvers)
        self.lifecycle.to("disabled", reason)
        self.audit.emit("provider.emergency_disable", "ok", ",".join(sorted(a.principal for a in approvers)), self.slot, reason)

    def enter_degraded(self, allowed_ops=None) -> None:
        from .resilience.failover import DEFAULT_DEGRADED_OPS
        self.degraded_ops = frozenset(allowed_ops or DEFAULT_DEGRADED_OPS)
        self.lifecycle.to("degraded", "degraded mode")
        self.audit.emit("provider.degraded", "ok", self.instance_id, self.slot, ",".join(sorted(self.degraded_ops)))

    def recover(self) -> None:
        self.degraded_ops = None
        self.lifecycle.to("ready", "recovered")

    def health(self) -> dict:
        self.health_model.set_dependency("backend", "ok" if self.backend.healthy() else "down")
        self.health_model.heartbeat()
        caps = sorted(self.degraded_ops) if self.degraded_ops else list(getattr(self.backend, "operations", []))
        return self.health_model.report(self.lifecycle.state, caps)

    # ------------------------------------------------------------------ helpers
    def _deny(self, action: str, who: str, subject: str, exc: ProviderFault, cid: str):
        self.audit.emit(action, "deny", who, subject, exc.code)
        self.metrics.inc("pk_denied", {"contract": self.contract_id, "code": exc.code})
        self.log.log("warn", action, outcome="deny", code=exc.code, correlation_id=cid, **{"explain": explain("deny", action, exc.code)})

    def _key(self, ident: IdentityContext, link_name: str) -> tuple:
        return ident.scope() + (link_name,)

    # ------------------------------------------------------------------ link mgmt
    def link(self, token: str, decision: dict, *, link_name: str, config: dict, secret_ref: str | None = None,
             author: str | None = None, reason: str = "link") -> dict:
        cid = new_correlation_id()
        who = "unauthenticated"
        action = "link.create"
        try:
            ident = self.authn.authenticate(token)
            who = ident.principal or ident.label()
            link_name = _validate_identifier(link_name, "link name")
            key = self._key(ident, link_name)
            exists = self.store.get(key) is not None
            action = "link.update" if exists else "link.create"
            if self.lifecycle.state not in SERVING_PROVIDER or self.degraded_ops is not None:
                raise ProviderFault("PK_PROVIDER_DISABLED", f"provider {self.lifecycle.state}; link changes refused")
            self.authz.enforce(decision, identity=ident, action=action, contract_id=self.contract_id, link_name=link_name)
            self.residency.check_placement(ident.tenant, region=self.region, environment=self.environment)
            safe = _validated_config(ident.component, config)
            if secret_ref is not None:
                self.secrets.validate_ref(secret_ref)
            self.quotas.check([tuple(k) for k, _ in self.store.items()], ident, safe, is_update=exists)
            self._fenced()
            rev = self.history.propose(key, {"config": safe, "secret_ref": secret_ref}, author=author or who, reason=reason)
            prev = self.store.get(key)
            tomb = self.store.revoked.get(json.dumps(list(key), separators=(",", ":")), 0)
            version = max(rev.version, (prev or {}).get("config_version", 0) + 1, tomb + 1)
            record = {"schema": "PK_PROVIDER_LINK/1", "identity": ident.as_dict(), "link_name": link_name,
                      "contract_id": self.contract_id, "config": safe, "config_version": version,
                      "residency": self.region}
            if secret_ref:
                record["secret_ref"] = secret_ref
            check(record, "pk_provider_link")
            self.store.put(key, record)  # durable before ack
            self.history.activate_batch([(key, rev.version)])
            m = self.link_states.get(key)
            if m is None or m.state == "revoked":
                m = link_machine()
                self.link_states[key] = m
            m.to("active", action)
            self.audit.emit(action, "allow", who, f"{ident.label()}#{link_name}", f"v{version}")
            self.metrics.gauge("pk_links", len(self.store.links), {"contract": self.contract_id})
            return {"link_name": link_name, "config_version": version, "correlation_id": cid}
        except ProviderFault as e:
            self._deny(action, who, link_name if isinstance(link_name, str) else "?", e, cid)
            raise
        except SchemaError as e:
            f = ProviderFault("PK_PROVIDER_INVALID_LINK", str(e)[:200])
            self._deny(action, who, "?", f, cid)
            raise f from None
        except Exception as e:  # validation errors from provider.py carry codes too
            code = getattr(e, "code", "PK_PROVIDER_ERROR")
            f = ProviderFault(code if code.startswith("PK_PROVIDER_") else "PK_PROVIDER_ERROR", str(e)[:200])
            self._deny(action, who, "?", f, cid)
            raise f from None

    def unlink(self, token: str, decision: dict, *, link_name: str) -> bool:
        cid = new_correlation_id()
        who = "unauthenticated"
        try:
            ident = self.authn.authenticate(token)
            who = ident.principal or ident.label()
            link_name = _validate_identifier(link_name, "link name")
            self.authz.enforce(decision, identity=ident, action="link.revoke", contract_id=self.contract_id, link_name=link_name)
            self._fenced()
            key = self._key(ident, link_name)
            ok = self.store.revoke(key)
            rec = None
            if ok:
                rec = self.link_states.get(key)
                if rec and rec.state != "revoked":
                    rec.to("revoked", "unlink")
                self.idem = IdempotencyCache()  # drop any cached results that could outlive the link
            self.audit.emit("link.revoke", "allow" if ok else "error", who, f"{ident.label()}#{link_name}", "revoked" if ok else "absent")
            return ok
        except ProviderFault as e:
            self._deny("link.revoke", who, str(link_name), e, cid)
            raise

    def link_names(self, token: str) -> list[str]:
        ident = self.authn.authenticate(token)
        return sorted(k[5] for k, _ in ((tuple(k), v) for k, v in self.store.items()) if k[:5] == ident.scope())

    # ------------------------------------------------------------------ calls
    def call(self, token: str, decision: dict, *, link_name: str, op: str, payload: dict | None = None,
             meta: dict | None = None, cancel: CancelToken | None = None) -> dict:
        t0 = time.perf_counter()
        meta = dict(meta or {})
        meta.setdefault("correlation_id", new_correlation_id())
        meta.setdefault("deadline_ms", 5000)
        cid = meta["correlation_id"] if isinstance(meta.get("correlation_id"), str) else new_correlation_id()
        who = "unauthenticated"
        try:
            try:
                check(meta, "call_metadata")
            except SchemaError as e:
                raise ProviderFault("PK_PROVIDER_INVALID_LINK", f"bad call metadata: {e}") from None
            trace_id, parent = parse_traceparent(meta.get("trace_parent"))
            ident = self.authn.authenticate(token)
            who = ident.principal or ident.label()
            link_name = _validate_identifier(link_name, "link name")
            op = _validate_identifier(op, "operation")
            if self.lifecycle.state not in SERVING_PROVIDER:
                raise ProviderFault("PK_PROVIDER_DISABLED", f"provider {self.lifecycle.state}")
            if self.degraded_ops is not None and not degraded_allows(op, self.degraded_ops):
                raise ProviderFault("PK_PROVIDER_UNAVAILABLE", "operation not available in degraded mode")
            self.authz.enforce(decision, identity=ident, action="call", contract_id=self.contract_id,
                               link_name=link_name, operation=op)
            key = self._key(ident, link_name)
            rec = self.store.get(key)
            state = self.link_states.get(key)
            if rec is None or state is None or state.state != "active":
                raise ProviderFault("PK_PROVIDER_NO_LINK", "no active link for caller scope")
            if tuple(rec["identity"][f] for f in ("tenant", "environment", "site", "workload", "component")) != ident.scope():
                self.metrics.inc("pk_isolation_violation", {"contract": self.contract_id})
                raise ProviderFault("PK_PROVIDER_FORBIDDEN", "link record scope mismatch")
            deadline = Deadline(meta["deadline_ms"])
            idem_key = meta.get("idempotency_key")
            req = {"op": op, "payload": payload, "link": link_name}
            if idem_key:
                hit = self.idem.lookup(key, idem_key, req)
                if hit is not None:
                    return dict(hit, idempotent_replay=True)
            with self.admission.admit(ident.tenant, key):
                def attempt(n):
                    self.breaker.before()
                    secret = None
                    if rec.get("secret_ref"):
                        secret = self.secrets.resolve(rec["secret_ref"], ident)
                        self.audit.emit("secret.use", "ok", who, f"{ident.label()}#{link_name}", rec["secret_ref"])
                    try:
                        res = self.dispatcher.run(
                            lambda: self.backend.invoke(op, rec["config"], secret, payload or {}),
                            deadline=deadline, cancel=cancel)
                    except ProviderFault as e:
                        if e.code in ("PK_PROVIDER_UNAVAILABLE", "PK_PROVIDER_DEADLINE_EXCEEDED"):
                            self.breaker.failure()
                        raise
                    except Exception:
                        self.breaker.failure()
                        raise ProviderFault("PK_PROVIDER_UNAVAILABLE", "backend error") from None
                    self.breaker.success()
                    return res
                with self.tracer.span("provider.call", trace_id, parent, op=op, contract=self.contract_id):
                    result = call_with_retry(attempt, op=op, deadline=deadline, idempotency_key=idem_key)
            out = {"op": op, "link": link_name, "config_version": rec["config_version"], "result": result,
                   "correlation_id": cid, "trace_id": trace_id}
            if idem_key:
                self.idem.store(key, idem_key, req, out)
            self.metrics.inc("pk_calls", {"contract": self.contract_id, "op": op[:32], "outcome": "ok"})
            self.metrics.observe("pk_dispatch_seconds", _ms_since(t0), {"contract": self.contract_id})
            return out
        except ProviderFault as e:
            self._deny("provider.call", who, str(link_name), e, cid)
            self.metrics.inc("pk_calls", {"contract": self.contract_id, "outcome": "error", "code": e.code})
            raise

    def error_envelope(self, exc: BaseException, correlation_id: str | None = None) -> dict:
        return to_envelope(exc, correlation_id)

    @staticmethod
    def canary_bucket(key: tuple) -> int:
        return zlib.crc32("|".join(key).encode()) % 100
