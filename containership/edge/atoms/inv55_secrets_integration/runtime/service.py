"""SecretsService - the public boundary (integrates every runtime layer).

Delivery model: the wire API (``handle``) returns a *lease handle*, never
plaintext.  Plaintext is obtained in-process through :meth:`use` by the same
authenticated workload (sidecar / SDK model), after identity, scope,
revocation, retirement, quarantine and expiry checks.  This keeps secret
values off every serialised boundary this component owns.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from . import RUNTIME_VERSION
from .audit import AuditLog
from .authz import ScopePolicy
from .cache import LeaseCache
from .config import digest as config_digest
from .errors import INV55Error, Outcome
from .identity import HmacTokenVerifier, Principal
from .negotiation import negotiate
from .provider import SecretProvider
from .quarantine import Quarantine
from .resilience import Bulkhead, CircuitBreaker, Deadline, TokenBucketQuota, retry
from .telemetry import JsonLogger, Metrics, Tracer
from .wire import SCHEMAS, validate


@dataclass
class _Lease:
    subject: str
    tenant: str
    app: str
    name: str
    version: int
    expires_at: float
    revoked: bool = False
    provider_lease_id: str | None = None


class SecretsService:
    def __init__(self, cfg: dict, provider: SecretProvider, verifier: HmacTokenVerifier, *, policy: ScopePolicy | None = None,
                 audit: AuditLog | None = None, clock=time.monotonic, wall=time.time, logger: JsonLogger | None = None,
                 max_leases: int = 100_000, sleep=time.sleep):
        self.cfg, self.cfg_digest = cfg, config_digest(cfg)
        self.provider, self.verifier = provider, verifier
        self.policy = policy or ScopePolicy()
        self.audit = audit or AuditLog()
        self.clock, self.wall, self.sleep = clock, wall, sleep
        self.metrics = Metrics(cfg["telemetry"]["max_series"])
        self.log = logger or JsonLogger()
        self.tracer = Tracer()
        self.quarantine = Quarantine()
        r, lim, c = cfg["retry"], cfg["limits"], cfg["cache"]
        self.breaker = CircuitBreaker(r.get("breaker_threshold", 5), r.get("breaker_cooldown_s", 10.0), clock)
        self.bulkhead = Bulkhead(lim["max_inflight"])
        self.quota = TokenBucketQuota(lim["rate_per_s"], lim["burst"], clock=clock)
        self.cache = LeaseCache(fresh_s=c["fresh_s"], max_stale_s=c["max_stale_s"], allow_stale=c["allow_stale"])
        self.max_request_bytes = lim.get("max_request_bytes", 16384)
        self._leases: "OrderedDict[str, _Lease]" = OrderedDict()
        self._retired: set[tuple[str, int]] = set()
        self._idem: "OrderedDict[str, tuple[str, dict]]" = OrderedDict()
        self.max_leases = max_leases
        self._lock = threading.RLock()
        self._last_now = None
        self.last_success_at = None
        self.inflight = 0

    # -- helpers -----------------------------------------------------------
    def _now(self):
        now = float(self.clock())
        if self._last_now is not None and now < self._last_now:
            raise INV55Error("INV55-E-CLOCK", "monotonic clock moved backwards")
        self._last_now = now
        return now

    def _audit(self, op, p: Principal | None, name, allowed, reason, version=None, code=None, rid=None, trace=None, policy_digest=None):
        self.audit.append(op=op, tenant=p.tenant if p else "-", app=p.app if p else "-", subject=p.subject if p else "-",
                          secret_ref=name or "-", version=version, allowed=allowed, reason=reason, code=code,
                          policy_digest=policy_digest or self.policy.digest, config_digest=self.cfg_digest,
                          request_id=rid, trace_id=trace, at=self.wall())

    def _provider_call(self, fn):
        r = self.cfg["retry"]
        dl = Deadline.after(r["deadline_s"], self.clock)
        return retry(lambda rem: self.breaker.call(fn, rem), attempts=r["attempts"], base_s=r["base_s"], cap_s=r["cap_s"],
                     deadline=dl, sleep=self.sleep,
                     on_retry=lambda n, code: self.metrics.inc("provider_retries", reason=code))

    # -- wire boundary -----------------------------------------------------
    def handle(self, op: str, raw: bytes | str, token: str) -> dict:
        t0 = time.perf_counter()
        trace = self.tracer.new_trace_id()
        rid = None
        p = None
        name = None
        try:
            if isinstance(raw, str):
                raw = raw.encode()
            if len(raw) > self.max_request_bytes:
                raise INV55Error("INV55-E-INVALID-REQUEST", "request too large", reason="too_large")
            try:
                req = json.loads(raw)
            except ValueError:
                raise INV55Error("INV55-E-INVALID-REQUEST", "unparseable", reason="unparseable") from None
            if not isinstance(req, dict):
                raise INV55Error("INV55-E-INVALID-REQUEST", reason="not_object")
            rid = req.get("request_id") if isinstance(req.get("request_id"), str) else None
            proto = negotiate(op, req.get("versions"))
            errs = validate(req, SCHEMAS[f"{proto}.request"])
            if errs:
                raise INV55Error("INV55-E-INVALID-REQUEST", "; ".join(errs[:5]), reason="schema")
            name = req["name"]
            with self.tracer.span(f"inv55.{op.lower()}", trace) as sp:
                sp.attrs = {"op": op}
                self._now()   # clock integrity before any time-based control
                p = self.verifier.verify(token, self.wall())
                self.quarantine.check(tenant=p.tenant, secret=name, op=op.lower())
                self.quota.take((p.tenant, p.app))
                with self.bulkhead:
                    with self._lock:
                        self.inflight += 1
                    try:
                        body = getattr(self, f"_{op.lower()}")(p, req, rid, trace)
                    finally:
                        with self._lock:
                            self.inflight -= 1
            self.metrics.inc("requests", op=op, tenant=p.tenant, outcome=body["outcome"])
            self.last_success_at = self.clock()
            return {"protocol": proto, "request_id": rid, **body}
        except INV55Error as e:
            self.metrics.inc("requests", op=op, tenant=p.tenant if p else "-", outcome=e.outcome.value)
            self.metrics.inc("denials" if e.outcome is Outcome.DENIED else "failures", op=op, reason=e.reason)
            if e.code != "INV55-E-DENIED" or p is None:   # authz denials are audited inside the op
                try:
                    self._audit(op.lower(), p, name, False, e.reason, code=e.code, rid=rid, trace=trace)
                except ValueError:
                    pass
            self.log.log("warn", "inv55.request_failed", op=op, code=e.code, reason=e.reason, request_id=rid, trace_id=trace)
            return e.to_wire(rid)
        except Exception as ex:   # fail closed; counted so tests can prove it never happens
            self.metrics.inc("internal_errors", op=op, kind=type(ex).__name__)
            self.log.log("error", "inv55.internal_error", op=op, kind=type(ex).__name__, request_id=rid, trace_id=trace)
            return INV55Error("INV55-E-INTERNAL").to_wire(rid)
        finally:
            self.metrics.observe_ms("request_latency", (time.perf_counter() - t0) * 1000, op=op)

    # -- operations ----------------------------------------------------------
    def _authorize(self, p, verb, name, rid, trace):
        d = self.policy.decide(p, verb, name)
        if not d.allowed:
            self._audit(verb, p, name, False, d.reason, code="INV55-E-DENIED", rid=rid, trace=trace, policy_digest=d.policy_digest)
            raise INV55Error("INV55-E-DENIED", d.reason, reason=d.reason)
        return d

    def _resolve(self, p, req, rid, trace):
        name = req["name"]
        d = self._authorize(p, "resolve", name, rid, trace)
        now = self._now()
        want = req.get("version")
        outcome = "SUCCESS"
        sec = self.cache.get_fresh(name, now) if want is None else None
        if sec is None:
            try:
                sec = self._provider_call(lambda rem: self.provider.read(name, want, timeout_s=rem))
                if want is None:
                    self.cache.put(sec, now)
            except INV55Error as e:
                stale = self.cache.get_stale(name, now) if (e.outcome is Outcome.RETRYABLE and want is None) else None
                if stale is None:
                    if e.code == "INV55-E-DENIED":   # provider not-found collapses to the same denial
                        self._audit("resolve", p, name, False, "denied_or_unavailable", code=e.code, rid=rid, trace=trace)
                    raise
                sec, outcome = stale, "DEGRADED"
                self.metrics.inc("degraded_served", tenant=p.tenant)
        if (name, sec.version) in self._retired:
            raise INV55Error("INV55-E-VERSION-RETIRED", reason="version_retired")
        ttl = min(float(req.get("ttl_s", self.cfg["lease"]["ttl_s"])), float(self.cfg["lease"]["max_ttl_s"]))
        lease_id = os.urandom(16).hex()
        with self._lock:
            if len(self._leases) >= self.max_leases:
                self._gc(now)
                if len(self._leases) >= self.max_leases:
                    raise INV55Error("INV55-E-OVERLOADED", "lease table full")
            self._leases[lease_id] = _Lease(p.subject, p.tenant, p.app, name, sec.version, now + ttl,
                                            provider_lease_id=sec.provider_lease_id)
        self._audit("resolve", p, name, True, "granted" if outcome == "SUCCESS" else "granted_degraded",
                    version=sec.version, rid=rid, trace=trace, policy_digest=d.policy_digest)
        self.metrics.inc("resolutions", tenant=p.tenant, outcome=outcome)
        return {"outcome": outcome, "lease": {"lease_id": lease_id, "name": name, "version": sec.version, "expires_in_s": ttl}}

    def _rotate(self, p, req, rid, trace):
        name = req["name"]
        self._authorize(p, "rotate", name, rid, trace)
        key = f"{p.subject}|{req['idempotency_key']}"
        fp = hashlib.sha256(json.dumps({k: req[k] for k in ("name", "expected_version") if k in req}, sort_keys=True).encode()).hexdigest()
        with self._lock:
            if key in self._idem:
                prev_fp, result = self._idem[key]
                if prev_fp != fp:
                    raise INV55Error("INV55-E-CONFLICT", reason="idempotency_key_reuse")
                return result
        value = (req.get("ext") or {}).get("value_ref")
        if not isinstance(value, str) or not value:
            raise INV55Error("INV55-E-INVALID-REQUEST", "rotate needs ext.value_ref", reason="missing_value")
        v = self._provider_call(lambda rem: self.provider.write(name, value, cas=req.get("expected_version"), timeout_s=rem))
        self.cache.invalidate(name)
        result = {"outcome": "SUCCESS", "lease": {"lease_id": "-", "name": name, "version": v, "expires_in_s": 0}}
        with self._lock:
            self._idem[key] = (fp, result)
            while len(self._idem) > 10_000:
                self._idem.popitem(last=False)
        self._audit("rotate", p, name, True, "rotated", version=v, rid=rid, trace=trace)
        self.metrics.inc("rotations", tenant=p.tenant)
        return result

    def _scope(self, p, req, rid, trace):
        name = req["name"]
        self._authorize(p, "scope.write", name, rid, trace)
        members = [tuple(m.split("/", 1)) for m in req["members"]]
        try:
            dg = self.policy.set_scope(name, members)
        except ValueError:
            raise INV55Error("INV55-E-DENIED", reason="cross_tenant_scope") from None
        self._audit("scope", p, name, True, "scope_set", rid=rid, trace=trace, policy_digest=dg)
        return {"outcome": "SUCCESS", "lease": {"lease_id": "-", "name": name, "version": 0, "expires_in_s": 0}}

    # -- in-process delivery -----------------------------------------------
    def use(self, lease_id: str, token: str) -> str:
        p = self.verifier.verify(token, self.wall())
        now = self._now()
        with self._lock:
            ls = self._leases.get(lease_id) if isinstance(lease_id, str) else None
        def deny(code, reason):
            self._audit("use", p, ls.name if ls else None, False, reason, code=code)
            self.metrics.inc("denials", op="use", reason=reason)
            raise INV55Error(code, reason=reason)
        if ls is None:
            deny("INV55-E-LEASE-CONTEXT", "unknown_lease")
        if ls.subject != p.subject:
            deny("INV55-E-LEASE-CONTEXT", "context_mismatch")
        self.quarantine.check(tenant=p.tenant, secret=ls.name, op="use")
        if ls.revoked:
            deny("INV55-E-LEASE-REVOKED", "revoked")
        if (ls.name, ls.version) in self._retired:
            deny("INV55-E-VERSION-RETIRED", "version_retired")
        if now >= ls.expires_at:
            self.metrics.inc("lease_expiries", tenant=p.tenant)
            deny("INV55-E-LEASE-EXPIRED", "expired")
        d = self.policy.decide(p, "use", ls.name)     # scope re-checked at use time
        if not d.allowed:
            deny("INV55-E-DENIED", d.reason)
        cached = self.cache.get_fresh(ls.name, now)
        sec = cached if cached is not None and cached.version == ls.version else \
            self._provider_call(lambda rem: self.provider.read(ls.name, ls.version, timeout_s=rem))
        self._audit("use", p, ls.name, True, "allowed", version=ls.version)
        return sec.value._reveal()

    # -- operator controls ---------------------------------------------------
    def revoke(self, lease_id: str, actor: str):
        with self._lock:
            ls = self._leases.get(lease_id)
            if ls is None:
                raise INV55Error("INV55-E-LEASE-CONTEXT", reason="unknown_lease")
            ls.revoked = True
        if ls.provider_lease_id:
            self._provider_call(lambda rem: self.provider.revoke_lease(ls.provider_lease_id, timeout_s=rem))
        self.audit.append(op="revoke", actor=actor, secret_ref=ls.name, version=ls.version, allowed=True, reason="operator_revoke", at=self.wall())

    def retire(self, name: str, version: int, actor: str, *, destroy: bool = False):
        with self._lock:
            self._retired.add((name, int(version)))
        self.cache.invalidate(name)
        if destroy:
            self._provider_call(lambda rem: self.provider.destroy_version(name, version, timeout_s=rem))
        self.audit.append(op="retire", actor=actor, secret_ref=name, version=version, allowed=True, reason="operator_retire", at=self.wall())

    def freeze(self, scope, reason, actor):
        self.quarantine.freeze(scope, reason)
        self.audit.append(op="freeze", actor=actor, reason=reason, detail=scope, allowed=True, at=self.wall())

    def unfreeze(self, scope, actor):
        self.quarantine.unfreeze(scope)
        self.audit.append(op="unfreeze", actor=actor, detail=scope, allowed=True, reason="operator_unfreeze", at=self.wall())

    def _gc(self, now):
        dead = [k for k, v in self._leases.items() if v.revoked or v.expires_at <= now]
        for k in dead:
            del self._leases[k]

    def explain(self, request_id: str) -> list[dict]:
        """Operator explain view (checklist #77): every audited decision for a request, secret-free."""
        return [r for r in self.audit.memory if r.get("request_id") == request_id]

    def state_snapshot(self) -> dict:
        """Crash/restart semantics (#57): leases are deliberately NOT persisted - a restart
        invalidates every outstanding lease (fail closed); scopes and retirements are."""
        return {"runtime": RUNTIME_VERSION, "scopes": {k: sorted(map(list, self.policy.scope_of(k)))
                                                        for k in list(self.policy._scopes)},
                "retired": sorted(map(list, self._retired)), "audit_head": self.audit.head, "config_digest": self.cfg_digest}

    def restore(self, snap: dict):
        for k, members in snap.get("scopes", {}).items():
            self.policy.set_scope(k, [tuple(m) for m in members])
        self._retired |= {(n, int(v)) for n, v in snap.get("retired", [])}
