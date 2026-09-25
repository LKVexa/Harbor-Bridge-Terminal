"""Production service façade for INV-55.

Wires provider + authentication + authorization + admission + retry/circuit breaker
+ durable audit + telemetry + lifecycle into the three public protocols:

* ``PK_SECRET_RESOLVE/1`` (resolve, use, revoke)  -- schemas/resolve.*.schema.json
* ``PK_SECRET_ROTATE/1``  (rotate, retire)          -- schemas/rotate.*.schema.json
* ``PK_SECRET_SCOPE/1``   (set/get scope)           -- schemas/scope.*.schema.json

Security invariants (docs/requirements/SRS.md):
  every operation authenticates -> admits -> authorizes -> audits (durably) -> acts;
  any failure in authn/authz/audit/clock fails closed; unauthorised and missing
  secrets are indistinguishable externally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
import re
import secrets as _rand
import threading
import time
from typing import Callable

from .audit import AuditChain
from .config import ConfigController
from .errors import ErrorCode, Inv55Error, error
from .identity import Authenticator, PolicyEngine, Principal
from .providers.base import (ProviderConflict, ProviderDenied, ProviderError, ProviderNotFound,
                             ProviderSecret, ProviderUnavailable, SecretProvider)
from .resilience import AdmissionController, CircuitBreaker, CircuitOpen, Deadline, RetryPolicy
from .secretvalue import SecretValue
from .telemetry import DecisionLedger, DecisionRecord, JsonLogger, Metrics, Tracer

__version__ = "4.3.0"
PROTOCOLS = {"PK_SECRET_RESOLVE": (1,), "PK_SECRET_ROTATE": (1,), "PK_SECRET_SCOPE": (1,)}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
PLATFORM_TENANT = "platform"      # only operators of this tenant may freeze/unfreeze the whole service


def valid_path_segments(value: str) -> bool:
    """Reject empty, '.' and '..' segments so names can never traverse provider paths."""
    return all(seg not in ("", ".", "..") for seg in value.split("/"))


class State(str, Enum):
    """Lifecycle state machine (docs/architecture/lifecycle.md)."""
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FROZEN = "frozen"
    QUARANTINED = "quarantined"
    DRAINING = "draining"
    STOPPED = "stopped"


TRANSITIONS = {
    State.STARTING: {State.READY, State.DEGRADED, State.STOPPED, State.QUARANTINED},
    State.READY: {State.DEGRADED, State.FROZEN, State.QUARANTINED, State.DRAINING},
    State.DEGRADED: {State.READY, State.FROZEN, State.QUARANTINED, State.DRAINING},
    State.FROZEN: {State.READY, State.DEGRADED, State.QUARANTINED, State.DRAINING},
    State.QUARANTINED: {State.DRAINING, State.FROZEN},   # leaving quarantine requires an operator unfreeze via FROZEN
    State.DRAINING: {State.STOPPED},
    State.STOPPED: set(),
}


@dataclass
class Lease:
    lease_id: str
    tenant: str
    subject: str
    name: str
    version: int
    issued_at: float
    expires_at: float
    value: SecretValue = field(repr=False)
    provider_lease_id: str | None = None
    revoked: bool = False


@dataclass
class ServiceLimits:
    max_secret_bytes: int = 65_536
    max_apps_per_scope: int = 1_024
    max_active_leases: int = 100_000
    max_leases_per_subject: int = 1_000
    lease_ttl_s: float = 300.0
    max_lease_ttl_s: float = 3_600.0
    cache_ttl_s: float = 30.0
    stale_grace_s: float = 0.0          # >0 permits DEGRADED serving from cache (disconnected policy)
    request_timeout_s: float = 2.0
    stall_after_s: float = 30.0


class SecretsService:
    def __init__(self, *, provider: SecretProvider, authenticator: Authenticator, policy: PolicyEngine,
                 audit: AuditChain, clock: Callable[[], float] = time.monotonic,
                 limits: ServiceLimits | None = None, metrics: Metrics | None = None,
                 logger: JsonLogger | None = None, tracer: Tracer | None = None,
                 config: ConfigController | None = None, release: str = __version__,
                 retry: RetryPolicy | None = None, breaker: CircuitBreaker | None = None,
                 admission: AdmissionController | None = None, state_path: str | None = None) -> None:
        self.provider, self.authn, self.policy, self.audit = provider, authenticator, policy, audit
        self._raw_clock = clock
        self.limits = limits or ServiceLimits()
        self.metrics = metrics or Metrics()
        self.logger = logger
        self.tracer = tracer or Tracer(self._raw_clock)  # raw: tracing must never raise
        self.config = config or ConfigController()
        self.release = release
        self.retry = retry or RetryPolicy()
        self.breaker = breaker or CircuitBreaker(self._now)
        self.admission = admission or AdmissionController(self._now)
        self.ledger = DecisionLedger()
        self.state = State.STARTING
        self._state_reason = "boot"
        self._leases: dict[str, Lease] = {}
        self._per_subject: dict[tuple[str, str], int] = {}
        self._scopes: dict[tuple[str, str], frozenset[str]] = {}
        self._retired: set[tuple[str, str, int]] = set()
        self._cache: dict[tuple[str, str], tuple[float, ProviderSecret]] = {}
        self._idem: dict[str, dict] = {}
        self._last_now: float | None = None
        self._last_progress: float | None = None
        self._lock = threading.RLock()
        self.state_path = state_path
        if state_path:
            self._load_state()

    # ------------------------------------------------------------------ durable control state (#57, #94)
    def _load_state(self) -> None:
        """Scopes and retirements survive restart; leases and caches deliberately do not."""
        import json, os
        if not os.path.exists(self.state_path):
            return
        with open(self.state_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("format") != "inv55-state/1":
            raise ValueError("unsupported state file format")
        self._scopes = {(s["tenant"], s["name"]): frozenset(s["apps"]) for s in data["scopes"]}
        self._retired = {(r["tenant"], r["name"], int(r["version"])) for r in data["retired"]}

    def _save_state(self, scopes=None, retired=None) -> None:
        """Persist the *prospective* state before it is applied in memory (write-ahead)."""
        if not self.state_path:
            return
        import json, os
        scopes = self._scopes if scopes is None else scopes
        retired = self._retired if retired is None else retired
        data = {"format": "inv55-state/1",
                "scopes": [{"tenant": t, "name": n, "apps": sorted(a)} for (t, n), a in sorted(scopes.items())],
                "retired": [{"tenant": t, "name": n, "version": v} for t, n, v in sorted(retired)]}
        tmp = self.state_path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.state_path)       # atomic swap: crash leaves old or new, never partial

    def export_state(self) -> dict:
        """Backup payload (docs/operations/backup-restore.md). Contains no secret values."""
        with self._lock:
            return {"format": "inv55-state/1",
                    "scopes": [{"tenant": t, "name": n, "apps": sorted(a)} for (t, n), a in sorted(self._scopes.items())],
                    "retired": [{"tenant": t, "name": n, "version": v} for t, n, v in sorted(self._retired)]}

    # ------------------------------------------------------------------ time & lifecycle
    def _now(self) -> float:
        now = float(self._raw_clock())
        if not math.isfinite(now):
            raise error(ErrorCode.CLOCK_ROLLBACK)
        last = self._last_now
        if last is not None and now < last:
            raise error(ErrorCode.CLOCK_ROLLBACK)
        self._last_now = now
        return now

    def transition(self, new: State, reason: str) -> None:
        with self._lock:
            if new not in TRANSITIONS[self.state]:
                raise ValueError(f"illegal transition {self.state.value} -> {new.value}")
            old, self.state, self._state_reason = self.state, new, reason
        self.metrics.inc("inv55_state_transitions_total", to=new.value)
        self._log("info", "state_transition", old=old.value, new=new.value, reason=reason)

    def start(self) -> State:
        """Deterministic bootstrap: config must be active, provider healthy -> READY, else DEGRADED."""
        if self.config.active is None:
            self.transition(State.QUARANTINED, "no_active_config")
            return self.state
        h = self.provider.health()
        self.transition(State.READY if h.reachable else State.DEGRADED,
                        "provider_ok" if h.reachable else "provider_unreachable")
        self._last_progress = self._now()
        return self.state

    def _operator(self, op: str, credential: str) -> Principal:
        """Global operator controls: platform-tenant operators only; every attempt is audited."""
        try:
            p = self.authn.authenticate(credential)
        except Inv55Error:
            self._audit(op, None, "*", False, "unauthenticated", None)
            raise
        if "operator" not in p.roles or p.tenant != PLATFORM_TENANT:
            self._audit(op, p, "*", False, "not_platform_operator", None)
            raise error(ErrorCode.DENIED)
        return p

    def freeze(self, principal_credential: str, reason: str) -> None:
        p = self._operator("freeze", principal_credential)
        reason = reason if isinstance(reason, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", reason) else "operator"
        self._audit("freeze", p, "*", True, reason, None)
        self.transition(State.FROZEN, reason)

    def unfreeze(self, principal_credential: str) -> None:
        p = self._operator("unfreeze", principal_credential)
        self._audit("unfreeze", p, "*", True, "operator", None)
        h = self.provider.health()
        self.transition(State.READY if h.reachable else State.DEGRADED, "operator_unfreeze")

    def quarantine(self, reason: str) -> None:
        """Automatic safety stop (e.g. audit chain divergence)."""
        with self._lock:
            for lease in self._leases.values():
                lease.revoked = True
        self.transition(State.QUARANTINED, reason)

    def drain(self) -> None:
        self.transition(State.DRAINING, "shutdown")
        with self._lock:
            for lease in self._leases.values():
                lease.value.wipe()
            self._leases.clear()
            self._cache.clear()
        self.transition(State.STOPPED, "drained")

    # ------------------------------------------------------------------ health (#52, #71)
    def health(self) -> dict:
        now = self._now()
        ph = self.provider.health()
        stalled = (self.state in (State.READY, State.DEGRADED) and self.admission.in_flight > 0
                   and self._last_progress is not None and now - self._last_progress > self.limits.stall_after_s)
        ready = self.state in (State.READY, State.DEGRADED) and not stalled
        return {
            "live": self.state is not State.STOPPED,
            "ready": ready,
            "state": self.state.value,
            "state_reason": self._state_reason,
            "stalled": stalled,
            "version": __version__,
            "release": self.release,
            "protocols": {k: list(v) for k, v in PROTOCOLS.items()},
            "config": self.config.provenance(),
            "policy_digest": self.policy.digest(),
            "dependencies": {
                "provider": {"name": getattr(self.provider, "name", "?"), "reachable": ph.reachable,
                             "sealed": ph.sealed, "version": ph.version, "detail": ph.detail},
                "circuit": self.breaker.state,
                "audit": {"seq": self.audit.seq, "head": self.audit.head},
            },
            "leases_active": len(self._leases),
            "in_flight": self.admission.in_flight,
        }

    # ------------------------------------------------------------------ internals
    def _log(self, level: str, event: str, **fields) -> None:
        if self.logger:
            self.logger.log(level, event, **fields)

    def _audit(self, op: str, p: Principal | None, name: str, allowed: bool, reason: str,
               version: int | None, request_id: str | None = None) -> None:
        try:
            self.audit.record({"op": op, "tenant": p.tenant if p else None, "subject": p.subject if p else None,
                               "secret": name, "allowed": allowed, "reason": reason, "version": version,
                               "request_id": request_id, "at": self._last_now})
        except OSError:
            self.metrics.inc("inv55_audit_failures_total")
            raise error(ErrorCode.AUDIT_UNAVAILABLE) from None

    def _decision(self, rid: str, op: str, p: Principal | None, name: str, outcome: str, reason: str,
                  trace_id: str | None) -> None:
        self.ledger.add(DecisionRecord(self._last_now or 0.0, rid, op, p.tenant if p else "-",
                                       p.subject if p else "-", name, outcome, reason, self.policy.digest(),
                                       (self.config.active.digest if self.config.active else "none"),
                                       self.release, trace_id))

    @staticmethod
    def _ident(value, field_name: str) -> str:
        if not isinstance(value, str) or not _ID.fullmatch(value) or not valid_path_segments(value):
            raise error(ErrorCode.INVALID_REFERENCE, f"{field_name} invalid")
        return value

    @staticmethod
    def negotiate(protocol: str, expected: str | None = None) -> tuple[str, int]:
        """Mixed-version negotiation (#22): accept NAME/<n> for supported n; tolerant of unknown fields;
        the protocol family must match the operation being invoked."""
        m = re.fullmatch(r"(PK_SECRET_[A-Z]+)/(\d{1,3})", protocol if isinstance(protocol, str) else "")
        if (not m or m.group(1) not in PROTOCOLS or int(m.group(2)) not in PROTOCOLS[m.group(1)]
                or (expected is not None and m.group(1) != expected)):
            raise error(ErrorCode.UNSUPPORTED_VERSION)
        return m.group(1), int(m.group(2))

    def _provider_call(self, fn, deadline: Deadline):
        try:
            return self.retry.run(lambda: self.breaker.call(fn), deadline)
        except CircuitOpen:
            raise error(ErrorCode.PROVIDER_UNAVAILABLE) from None
        except ProviderUnavailable:
            raise error(ErrorCode.PROVIDER_UNAVAILABLE) from None
        except (ProviderNotFound, ProviderDenied):
            raise error(ErrorCode.DENIED) from None
        except ProviderConflict:
            raise
        except ProviderError:
            raise error(ErrorCode.PROVIDER_UNAVAILABLE) from None

    def _guard(self, op: str, credential: str, action: str, name: str, rid: str, trace_id: str | None
               ) -> Principal:
        if self.state in (State.FROZEN, State.QUARANTINED, State.DRAINING, State.STOPPED, State.STARTING):
            raise error(ErrorCode.FROZEN)
        try:
            p = self.authn.authenticate(credential)
        except Inv55Error:
            self.metrics.inc("inv55_denials_total", reason="unauthenticated")
            self._audit(op, None, name, False, "unauthenticated", None, rid)
            self._decision(rid, op, None, name, "denied", "unauthenticated", trace_id)
            raise
        self.admission.charge(p.tenant, p.subject)
        d = self.policy.decide(p, action, name)
        if not d.allowed:
            self.metrics.inc("inv55_denials_total", reason=d.reason)
            self._audit(op, p, name, False, d.reason, None, rid)
            self._decision(rid, op, p, name, "denied", d.reason, trace_id)
            raise error(ErrorCode.DENIED)
        return p

    def _run(self, op: str, request: dict, handler) -> dict:
        if not isinstance(request, dict):
            return {"ok": False, "error": Inv55Error(code=ErrorCode.INVALID_REFERENCE).to_wire()}
        rid = request.get("request_id") if isinstance(request.get("request_id"), str) else _rand.token_hex(8)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", rid):
            rid = _rand.token_hex(8)
        span = self.tracer.start(op, request.get("traceparent"), op=op)
        start = time.perf_counter()
        admitted = False
        try:
            self._now()
            self.admission.admit()
            admitted = True
            timeout = request.get("timeout_ms")
            t = self.limits.request_timeout_s if not isinstance(timeout, int) else min(max(timeout, 1) / 1000,
                                                                                       self.limits.request_timeout_s)
            deadline = Deadline.after(t, self._now)
            result = handler(rid, deadline, span.trace_id)
            outcome = result.get("outcome", "success")
            self.metrics.inc("inv55_requests_total", op=op, outcome=outcome)
            self._last_progress = self._now()
            result.update({"request_id": rid})
            return result
        except Inv55Error as exc:
            self.metrics.inc("inv55_requests_total", op=op, outcome=exc.code.value.outcome.value)
            self.tracer.finish(span, error=exc.code.value.code)
            span = None
            return {"ok": False, "error": exc.to_wire(rid)}
        except Exception as exc:  # fail closed on anything unexpected; never leak the exception text
            self.metrics.inc("inv55_requests_total", op=op, outcome="terminal")
            self.metrics.inc("inv55_internal_errors_total", kind=type(exc).__name__[:64])
            self._log("error", "internal_error", op=op, kind=type(exc).__name__, request_id=rid)
            return {"ok": False, "error": Inv55Error(code=ErrorCode.INTERNAL).to_wire(rid)}
        finally:
            if admitted:
                self.admission.release()
            self.metrics.observe("inv55_request_seconds", time.perf_counter() - start, op=op)
            if span is not None:
                self.tracer.finish(span)

    # ------------------------------------------------------------------ PK_SECRET_SCOPE/1
    def set_scope(self, request: dict) -> dict:
        def h(rid, deadline, trace):
            self.negotiate(request.get("protocol", ""), "PK_SECRET_SCOPE")
            name = self._ident(request.get("name"), "name")
            apps = request.get("apps")
            if not isinstance(apps, list) or not apps or len(apps) > self.limits.max_apps_per_scope:
                raise error(ErrorCode.LIMIT_EXCEEDED if isinstance(apps, list) and apps else ErrorCode.INVALID_REFERENCE)
            apps_n = frozenset(self._ident(a, "app") for a in apps)
            p = self._guard("scope", request.get("credential"), "scope", name, rid, trace)
            self._audit("scope", p, name, True, "requested", None, rid)
            with self._lock:
                self._save_state(scopes={**self._scopes, (p.tenant, name): apps_n})
                self._scopes[(p.tenant, name)] = apps_n
                # scope narrowing revokes leases of apps that lost access (fail-closed)
                for lease in self._leases.values():
                    if lease.tenant == p.tenant and lease.name == name and lease.subject not in apps_n:
                        lease.revoked = True
            self._audit("scope", p, name, True, "applied", None, rid)
            self._decision(rid, "scope", p, name, "allowed", "rule_match", trace)
            return {"ok": True, "outcome": "success", "protocol": "PK_SECRET_SCOPE/1", "name": name,
                    "apps": sorted(apps_n)}
        return self._run("scope", request, h)

    # ------------------------------------------------------------------ PK_SECRET_RESOLVE/1
    def resolve(self, request: dict) -> dict:
        def h(rid, deadline, trace):
            self.negotiate(request.get("protocol", ""), "PK_SECRET_RESOLVE")
            name = self._ident(request.get("name"), "name")
            p = self._guard("resolve", request.get("credential"), "resolve", name, rid, trace)
            with self._lock:
                allowed = self._scopes.get((p.tenant, name), frozenset())
            if p.subject not in allowed:
                self.metrics.inc("inv55_denials_total", reason="out_of_scope")
                self._audit("resolve", p, name, False, "out_of_scope", None, rid)
                self._decision(rid, "resolve", p, name, "denied", "out_of_scope", trace)
                raise error(ErrorCode.DENIED)
            key = (p.tenant, name)
            pname = f"{p.tenant}/{name}"
            outcome = "success"
            now = self._now()
            cached = self._cache.get(key)
            try:
                if cached and now - cached[0] <= self.limits.cache_ttl_s:
                    ps = cached[1]
                else:
                    ps = self._provider_call(lambda: self.provider.read(pname), deadline)
                    self._cache[key] = (now, ps)
                    if self.state is State.DEGRADED:
                        self.transition(State.READY, "provider_recovered")
            except Inv55Error as exc:
                if (exc.code is ErrorCode.PROVIDER_UNAVAILABLE and cached and self.limits.stale_grace_s > 0
                        and now - cached[0] <= self.limits.cache_ttl_s + self.limits.stale_grace_s):
                    ps, outcome = cached[1], "degraded"
                    if self.state is State.READY:
                        self.transition(State.DEGRADED, "provider_unavailable_serving_cache")
                else:
                    if exc.code is ErrorCode.DENIED:
                        self._audit("resolve", p, name, False, "denied_or_unavailable", None, rid)
                    raise
            if (p.tenant, name, ps.version) in self._retired:
                self._audit("resolve", p, name, False, "version_retired", ps.version, rid)
                raise error(ErrorCode.VERSION_RETIRED)
            ttl = request.get("ttl_s", self.limits.lease_ttl_s)
            if not isinstance(ttl, (int, float)) or isinstance(ttl, bool) or not math.isfinite(ttl) or ttl <= 0:
                raise error(ErrorCode.INVALID_REFERENCE)
            ttl = min(float(ttl), self.limits.max_lease_ttl_s)
            with self._lock:
                if len(self._leases) >= self.limits.max_active_leases:
                    self._expire_leases(now)
                    if len(self._leases) >= self.limits.max_active_leases:
                        raise error(ErrorCode.OVERLOADED)
                sk = (p.tenant, p.subject)
                if self._per_subject.get(sk, 0) >= self.limits.max_leases_per_subject:
                    raise error(ErrorCode.QUOTA_EXCEEDED)
                self._audit("resolve", p, name, True, "granted" if outcome == "success" else "granted_degraded",
                            ps.version, rid)
                lease = Lease(_rand.token_urlsafe(24), p.tenant, p.subject, name, ps.version, now, now + ttl,
                              ps.value, ps.provider_lease_id)
                self._leases[lease.lease_id] = lease
                self._per_subject[sk] = self._per_subject.get(sk, 0) + 1
            self.metrics.inc("inv55_resolutions_total", outcome=outcome)
            self._decision(rid, "resolve", p, name, "allowed", "rule_match", trace)
            return {"ok": True, "outcome": outcome, "protocol": "PK_SECRET_RESOLVE/1", "name": name,
                    "version": ps.version, "lease_id": lease.lease_id, "expires_in_s": ttl}
        return self._run("resolve", request, h)

    def _expire_leases(self, now: float) -> None:
        for lid in [k for k, v in self._leases.items() if now >= v.expires_at or v.revoked]:
            self._drop(lid)
            self.metrics.inc("inv55_lease_expiries_total")

    def _drop(self, lid: str) -> None:
        lease = self._leases.pop(lid, None)
        if lease:
            sk = (lease.tenant, lease.subject)
            self._per_subject[sk] = max(0, self._per_subject.get(sk, 1) - 1)

    def use(self, request: dict) -> dict:
        """Reveal the leased value.  The only code path that returns plaintext."""
        def h(rid, deadline, trace):
            self.negotiate(request.get("protocol", ""), "PK_SECRET_RESOLVE")
            name = self._ident(request.get("name"), "name")
            lid = request.get("lease_id")
            p = self._guard("use", request.get("credential"), "use", name, rid, trace)
            now = self._now()
            with self._lock:
                lease = self._leases.get(lid) if isinstance(lid, str) else None
                if lease is None or lease.tenant != p.tenant or lease.subject != p.subject or lease.name != name:
                    self._audit("use", p, name, False, "context_mismatch", None, rid)
                    raise error(ErrorCode.CONTEXT_MISMATCH)
                if lease.revoked:
                    self._audit("use", p, name, False, "revoked", lease.version, rid)
                    raise error(ErrorCode.LEASE_REVOKED)
                if (p.tenant, name, lease.version) in self._retired:
                    self._audit("use", p, name, False, "version_retired", lease.version, rid)
                    raise error(ErrorCode.VERSION_RETIRED)
                if now >= lease.expires_at:
                    self._audit("use", p, name, False, "expired", lease.version, rid)
                    self._drop(lid)
                    self.metrics.inc("inv55_lease_expiries_total")
                    raise error(ErrorCode.LEASE_EXPIRED)
                self._audit("use", p, name, True, "allowed", lease.version, rid)
                value = lease.value.reveal()
            self._decision(rid, "use", p, name, "allowed", "lease_valid", trace)
            return {"ok": True, "outcome": "success", "protocol": "PK_SECRET_RESOLVE/1", "name": name,
                    "version": lease.version, "value": value}
        return self._run("use", request, h)

    def revoke(self, request: dict) -> dict:
        def h(rid, deadline, trace):
            self.negotiate(request.get("protocol", ""), "PK_SECRET_RESOLVE")
            name = self._ident(request.get("name"), "name")
            p = self._guard("revoke", request.get("credential"), "revoke", name, rid, trace)
            lid = request.get("lease_id")
            with self._lock:
                lease = self._leases.get(lid) if isinstance(lid, str) else None
                if lease is None or lease.tenant != p.tenant or lease.name != name:
                    self._audit("revoke", p, name, False, "context_mismatch", None, rid)
                    raise error(ErrorCode.CONTEXT_MISMATCH)
                # secret-admins may revoke any lease on the secret within their tenant (incident response)
                self._audit("revoke", p, name, True, "revoked" if lease.subject == p.subject
                            else "revoked_by_admin", lease.version, rid)
                lease.revoked = True
                plid = lease.provider_lease_id
            if plid:
                self._provider_call(lambda: self.provider.revoke(plid), deadline)
            return {"ok": True, "outcome": "success", "protocol": "PK_SECRET_RESOLVE/1", "revoked": True}
        return self._run("revoke", request, h)

    # ------------------------------------------------------------------ PK_SECRET_ROTATE/1
    def rotate(self, request: dict) -> dict:
        def h(rid, deadline, trace):
            self.negotiate(request.get("protocol", ""), "PK_SECRET_ROTATE")
            name = self._ident(request.get("name"), "name")
            idem = request.get("idempotency_key")
            if not isinstance(idem, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", idem):
                raise error(ErrorCode.INVALID_REFERENCE, "idempotency_key required")
            value = request.get("value")
            if not isinstance(value, str) or not value or len(value.encode()) > self.limits.max_secret_bytes:
                raise error(ErrorCode.LIMIT_EXCEEDED if isinstance(value, str) and value else ErrorCode.INVALID_REFERENCE)
            p = self._guard("rotate", request.get("credential"), "rotate", name, rid, trace)
            ikey = f"{p.tenant}/{name}/{idem}"
            pname = f"{p.tenant}/{name}"
            expected = request.get("expected_version")
            if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool) or expected < 0):
                raise error(ErrorCode.INVALID_REFERENCE)
            import hashlib
            vhash = hashlib.sha256(b"inv55-idem\0" + value.encode()).hexdigest()
            # Reserve the idempotency key atomically: exactly one request per key performs the write;
            # duplicates wait for it and replay its result.  A different payload under the same key is a CONFLICT.
            with self._lock:
                entry = self._idem.get(ikey)
                owner = entry is None
                if owner:
                    entry = {"hash": vhash, "done": threading.Event(), "result": None}
                    while len(self._idem) >= 100_000:
                        oldest = next((k for k, v in self._idem.items() if v["done"].is_set()), None)
                        if oldest is None:
                            raise error(ErrorCode.OVERLOADED)
                        self._idem.pop(oldest)
                    self._idem[ikey] = entry
            if not owner:
                if entry["hash"] != vhash:
                    self._audit("rotate", p, name, False, "idempotency_payload_mismatch", None, rid)
                    raise error(ErrorCode.CONFLICT)
                entry["done"].wait(max(0.0, deadline.remaining()))
                if entry["result"] is None:
                    raise error(ErrorCode.CONFLICT if entry["done"].is_set() else ErrorCode.DEADLINE_EXCEEDED)
                prior = dict(entry["result"])
                prior["replayed"] = True
                return prior
            try:
                self._audit("rotate", p, name, True, "requested", None, rid)
                sv = SecretValue(value)
                try:
                    version = self._provider_call(lambda: self.provider.write(pname, sv, cas=expected), deadline)
                except ProviderConflict:
                    self._audit("rotate", p, name, False, "cas_conflict", None, rid)
                    raise error(ErrorCode.CONFLICT) from None
            except BaseException:
                with self._lock:
                    self._idem.pop(ikey, None)      # failed attempt: key may be retried
                entry["done"].set()
                raise
            result = {"ok": True, "outcome": "success", "protocol": "PK_SECRET_ROTATE/1", "name": name,
                      "version": version, "replayed": False}
            with self._lock:
                self._cache.pop((p.tenant, name), None)
                entry["result"] = dict(result)
            entry["done"].set()
            self._audit("rotate", p, name, True, "rotated", version, rid)
            self.metrics.inc("inv55_rotations_total")
            self._decision(rid, "rotate", p, name, "allowed", "rule_match", trace)
            return result
        return self._run("rotate", request, h)

    def retire(self, request: dict) -> dict:
        def h(rid, deadline, trace):
            self.negotiate(request.get("protocol", ""), "PK_SECRET_ROTATE")
            name = self._ident(request.get("name"), "name")
            version = request.get("version")
            if not isinstance(version, int) or isinstance(version, bool) or version < 1:
                raise error(ErrorCode.INVALID_REFERENCE)
            p = self._guard("retire", request.get("credential"), "retire", name, rid, trace)
            self._audit("retire", p, name, True, "requested", version, rid)
            with self._lock:
                self._save_state(retired=self._retired | {(p.tenant, name, version)})
                self._retired.add((p.tenant, name, version))
                self._cache.pop((p.tenant, name), None)
            self._audit("retire", p, name, True, "retired", version, rid)
            if request.get("destroy") is True:
                self._provider_call(lambda: self.provider.destroy_version(f"{p.tenant}/{name}", version), deadline)
            return {"ok": True, "outcome": "success", "protocol": "PK_SECRET_ROTATE/1", "name": name,
                    "version": version, "retired": True}
        return self._run("retire", request, h)
