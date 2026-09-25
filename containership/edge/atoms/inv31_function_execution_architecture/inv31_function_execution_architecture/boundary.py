"""Authenticated, authorized, observable invocation boundary for INV-31.

This module wraps :class:`runtime.FunctionPool` without changing its reuse rule.
It addresses checklist items that concern the *boundary* of the component:

* C023/C044  authentication of every caller (HMAC-SHA256 signed assertions,
             keys injected by the parent platform; an empty key store refuses all)
* C024/C042  explicit capabilities, least privilege, tenant binding
* C025/C053  deadlines, cancellation, idempotency keys, backpressure codes
* C016/C027  request-schema version negotiation
* C017       per-tenant instance quotas and bounded share of the pool
* C048/C056  fail-closed on critical dependencies, degraded mode on noncritical
* C049       tamper-evident, hash-chained audit events
* C071-C077  health/readiness, metrics, structured logs, trace context, explain

It contains no identity provider, no KMS and no network transport: those are
parent-platform responsibilities and remain BLOCKED items in the remediation
status, not features claimed here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from threading import Event, RLock
from typing import Any, Iterable, Mapping

from .errors import (
    AuthenticationFailed,
    AuthorizationDenied,
    Cancelled,
    DeadlineExceeded,
    DependencyUnavailable,
    Draining,
    IdempotencyConflict,
    Inv31Error,
    QuotaExceeded,
    ReplayDetected,
    UnsupportedVersion,
    to_error,
)
from .runtime import FunctionPool, _validate_identifier, _validate_tick

REQUEST_SCHEMA = "PK_INVOKE_REQUEST/1"
SUPPORTED_REQUEST_SCHEMAS: frozenset[str] = frozenset({REQUEST_SCHEMA})
RESPONSE_SCHEMA = "PK_INVOCATION/1"
MAX_ASSERTION_LIFETIME = 600  # logical ticks
MAX_NONCES = 65536
MAX_IDEMPOTENCY_ENTRIES = 4096
MAX_LOG_RECORDS = 10000
MAX_AUDIT_EVENTS = 100000
MAX_LATENCY_SAMPLES = 100000
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

CAP_OBSERVE = "pool:observe"
CAP_DRAIN = "pool:drain"
CAP_CONFIG = "config:apply"
CRITICAL_DEPENDENCIES = ("PLN-04 Execution plane",)
NONCRITICAL_DEPENDENCIES = ("INV-26 MicroVM snapshotting", "PLN-05 Elasticity plane",
                            "GAP-09 Unified observability")


def invoke_capability(tenant: str) -> str:
    return f"invoke:{tenant}"


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def redact_tenant(tenant: str) -> str:
    """Stable pseudonymous tenant handle for high-cardinality telemetry (C075)."""
    return "t:" + hashlib.sha256(tenant.encode()).hexdigest()[:12]


# --------------------------------------------------------------------------- authn

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    capabilities: frozenset[str]
    kind: str  # "service" | "human" | "operator"


class HmacAuthenticator:
    """Verifies caller assertions signed with keys supplied by the parent platform.

    No key is built in.  An authenticator with no keys refuses every caller,
    which is the safe behaviour when the identity/key service is unavailable.
    """

    def __init__(self, keys: Mapping[str, bytes] | None = None) -> None:
        self._keys: dict[str, bytes] = {}
        self._nonces: OrderedDict[str, int] = OrderedDict()
        self._lock = RLock()
        for key_id, key in (keys or {}).items():
            self.add_key(key_id, key)

    def add_key(self, key_id: str, key: bytes) -> None:
        _validate_identifier(key_id, "key_id")
        if not isinstance(key, (bytes, bytearray)) or len(key) < 32:
            raise ValueError("signing keys must be at least 32 bytes")
        with self._lock:
            self._keys[key_id] = bytes(key)

    def revoke_key(self, key_id: str) -> None:
        with self._lock:
            self._keys.pop(key_id, None)

    @property
    def available(self) -> bool:
        with self._lock:
            return bool(self._keys)

    @staticmethod
    def sign(key: bytes, claims: Mapping[str, Any]) -> dict[str, Any]:
        """Helper for callers/tests: produce a signed assertion."""
        body = dict(claims)
        body.pop("sig", None)
        body["sig"] = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
        return body

    def authenticate(self, assertion: Mapping[str, Any], now: int) -> Principal:
        now = _validate_tick(now)
        if not isinstance(assertion, Mapping):
            raise AuthenticationFailed("assertion must be an object")
        body = dict(assertion)
        sig = body.pop("sig", None)
        key_id = body.get("key_id")
        with self._lock:
            key = self._keys.get(key_id) if isinstance(key_id, str) else None
            if key is None:
                raise AuthenticationFailed("unknown or revoked signing key")
            if not isinstance(sig, str):
                raise AuthenticationFailed("missing signature")
            expected = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                raise AuthenticationFailed("signature mismatch")
            try:
                subject = _validate_identifier(body["subject"], "subject")
                tenant = _validate_identifier(body["tenant"], "tenant")
                issued = _validate_tick(body["issued_at"], "issued_at")
                expires = _validate_tick(body["expires_at"], "expires_at")
                nonce = _validate_identifier(body["nonce"], "nonce")
                caps = body["capabilities"]
                kind = body.get("kind", "service")
            except (KeyError, TypeError, ValueError) as exc:
                raise AuthenticationFailed(f"malformed assertion: {exc}") from None
            if not isinstance(caps, list) or not all(isinstance(c, str) for c in caps):
                raise AuthenticationFailed("capabilities must be a list of strings")
            if kind not in ("service", "human", "operator"):
                raise AuthenticationFailed("unknown principal kind")
            if expires <= issued or expires - issued > MAX_ASSERTION_LIFETIME:
                raise AuthenticationFailed("assertion lifetime outside policy")
            if now < issued:
                raise AuthenticationFailed("assertion issued in the future (clock rollback?)")
            if now >= expires:
                raise AuthenticationFailed("assertion expired")
            nonce_key = f"{key_id}:{nonce}"
            if nonce_key in self._nonces:
                raise ReplayDetected("assertion nonce already used")
            self._nonces[nonce_key] = expires
            while len(self._nonces) > MAX_NONCES:
                self._nonces.popitem(last=False)
            # Expired nonces can be forgotten: an expired assertion is refused anyway.
            for k in [k for k, exp in self._nonces.items() if exp <= now]:
                del self._nonces[k]
        return Principal(subject, tenant, frozenset(caps), kind)


# --------------------------------------------------------------------------- audit

class AuditLog:
    """Append-only SHA-256 hash chain (C049).  Tampering is detected by verify()."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._lock = RLock()

    @property
    def head(self) -> str:
        with self._lock:
            return self.events[-1]["hash"] if self.events else self.GENESIS

    def append(self, action: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            if len(self.events) >= MAX_AUDIT_EVENTS:
                raise DependencyUnavailable("audit log full; export required",
                                            dependency="audit-export")
            event = {"seq": len(self.events), "action": action, "prev": self.head, **fields}
            event["hash"] = hashlib.sha256(canonical(event)).hexdigest()
            self.events.append(event)
            return event

    def verify(self) -> bool:
        with self._lock:
            prev = self.GENESIS
            for seq, event in enumerate(self.events):
                body = {k: v for k, v in event.items() if k != "hash"}
                if body.get("seq") != seq or body.get("prev") != prev:
                    return False
                if hashlib.sha256(canonical(body)).hexdigest() != event["hash"]:
                    return False
                prev = event["hash"]
            return True


# --------------------------------------------------------------------------- telemetry

class Telemetry:
    """Bounded in-process metrics and structured logs (C072/C073/C075)."""

    def __init__(self, component: str = "INV-31", node: str = "local") -> None:
        self.component = component
        self.node = node
        self.counters: dict[str, int] = {}
        self.latency_ns: deque[int] = deque(maxlen=MAX_LATENCY_SAMPLES)
        self.logs: deque[dict[str, Any]] = deque(maxlen=MAX_LOG_RECORDS)
        self.export_buffer: deque[dict[str, Any]] = deque(maxlen=MAX_LOG_RECORDS)
        self._lock = RLock()

    def incr(self, name: str, n: int = 1) -> None:
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + n

    def log(self, operation: str, *, tenant: str | None, outcome: str,
            trace_id: str, span_id: str, **extra: Any) -> dict[str, Any]:
        record = {
            "schema": "PK_INV31_LOG/1",
            "component": self.component,
            "node": self.node,
            "operation": operation,
            "tenant": redact_tenant(tenant) if tenant else None,
            "outcome": outcome,
            "trace_id": trace_id,
            "span_id": span_id,
            **{k: v for k, v in extra.items() if k in ("code", "instance", "cold", "workload")},
        }
        with self._lock:
            self.logs.append(record)
            if len(self.export_buffer) == self.export_buffer.maxlen:
                self.counters["telemetry_dropped"] = self.counters.get("telemetry_dropped", 0) + 1
            self.export_buffer.append(record)
        return record

    def percentiles(self) -> dict[str, int | None]:
        with self._lock:
            data = sorted(self.latency_ns)
        if not data:
            return {"p50": None, "p95": None, "p99": None, "max": None}

        def pct(p: float) -> int:
            return data[min(len(data) - 1, int(round(p * (len(data) - 1))))]
        return {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99), "max": data[-1]}


def child_trace(traceparent: str | None) -> tuple[str, str, str | None]:
    """Return (trace_id, span_id, parent_span) honouring W3C traceparent (C074)."""
    if traceparent is not None:
        m = _TRACEPARENT.match(traceparent) if isinstance(traceparent, str) else None
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            return m.group(1), secrets.token_hex(8), m.group(2)
    return secrets.token_hex(16), secrets.token_hex(8), None


# --------------------------------------------------------------------------- control

class CancelToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass
class TenantQuota:
    max_instances: int

    def __post_init__(self) -> None:
        if isinstance(self.max_instances, bool) or not isinstance(self.max_instances, int) \
                or self.max_instances <= 0:
            raise ValueError("tenant max_instances must be a positive integer")


@dataclass
class Gateway:
    """The single authenticated entry point in front of a FunctionPool."""

    pool: FunctionPool
    authenticator: HmacAuthenticator
    default_quota: TenantQuota | None = None
    quotas: dict[str, TenantQuota] = field(default_factory=dict)
    max_tenant_share: float = 0.5
    audit: AuditLog = field(default_factory=AuditLog)
    telemetry: Telemetry = field(default_factory=Telemetry)
    dependencies: dict[str, bool] = field(default_factory=lambda: {
        d: True for d in (*CRITICAL_DEPENDENCIES, *NONCRITICAL_DEPENDENCIES)})
    disabled_reason: str | None = None
    _idem: OrderedDict[tuple[str, str], tuple[str, dict[str, Any]]] = field(
        default_factory=OrderedDict, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not (0 < self.max_tenant_share <= 1):
            raise ValueError("max_tenant_share must be in (0, 1]")
        if self.default_quota is None:
            self.default_quota = TenantQuota(
                max(1, int(self.pool.max_instances * self.max_tenant_share)))

    # ---- helpers
    def quota_for(self, tenant: str) -> TenantQuota:
        return self.quotas.get(tenant, self.default_quota)  # type: ignore[return-value]

    def set_dependency(self, name: str, up: bool) -> None:
        if name not in self.dependencies:
            raise ValueError(f"unknown dependency {name!r}")
        self.dependencies[name] = bool(up)

    def degraded(self) -> list[str]:
        return [d for d in NONCRITICAL_DEPENDENCIES if not self.dependencies.get(d, False)]

    def _authorize(self, principal: Principal, capability: str) -> None:
        if capability not in principal.capabilities:
            raise AuthorizationDenied("capability not granted", capability=capability)

    def _fail(self, op: str, exc: BaseException, tenant: str | None,
              trace: tuple[str, str, str | None], started: int) -> dict[str, Any]:
        err = to_error(exc)
        self.telemetry.incr(f"errors.{err['code']}")
        self.telemetry.latency_ns.append(time.perf_counter_ns() - started)
        self.telemetry.log(op, tenant=tenant, outcome="error", trace_id=trace[0],
                           span_id=trace[1], code=err["code"])
        if err["code"] in ("INV31-E-AUTHN", "INV31-E-AUTHZ", "INV31-E-REPLAY"):
            try:
                self.audit.append("security.reject", op=op, code=err["code"],
                                  tenant=redact_tenant(tenant) if tenant else None,
                                  trace_id=trace[0])
            except Inv31Error:
                pass
        return {"ok": False, "error": err, "trace_id": trace[0]}

    # ---- operations
    def invoke(self, assertion: Mapping[str, Any], request: Mapping[str, Any], *, now: int,
               deadline: int | None = None, cancel: CancelToken | None = None,
               traceparent: str | None = None) -> dict[str, Any]:
        started = time.perf_counter_ns()
        trace = child_trace(traceparent)
        tenant: str | None = None
        self.telemetry.incr("requests")
        try:
            now = _validate_tick(now)
            if not isinstance(request, Mapping):
                raise UnsupportedVersion("request must be an object", requested=None,
                                         supported=sorted(SUPPORTED_REQUEST_SCHEMAS))
            schema = request.get("schema")
            if schema not in SUPPORTED_REQUEST_SCHEMAS:
                raise UnsupportedVersion("unsupported request schema",
                                         requested=str(schema)[:64],
                                         supported=sorted(SUPPORTED_REQUEST_SCHEMAS))
            unknown = set(request) - {"schema", "tenant", "version", "idempotency_key", "workload"}
            if unknown:
                raise UnsupportedVersion("unknown request fields",
                                         requested=sorted(unknown)[:8],
                                         supported=sorted(SUPPORTED_REQUEST_SCHEMAS))
            tenant = _validate_identifier(request.get("tenant"), "tenant")
            version = _validate_identifier(request.get("version"), "version")
            principal = self.authenticator.authenticate(assertion, now)
            if principal.tenant != tenant:
                raise AuthorizationDenied("principal is bound to a different tenant",
                                          capability=invoke_capability(tenant))
            self._authorize(principal, invoke_capability(tenant))
            if self.disabled_reason is not None:
                raise Draining("component emergency-disabled")
            for dep in CRITICAL_DEPENDENCIES:
                if not self.dependencies.get(dep, False):
                    raise DependencyUnavailable("critical dependency unavailable", dependency=dep)
            if cancel is not None and cancel.cancelled:
                raise Cancelled("cancelled before admission")
            if deadline is not None:
                deadline = _validate_tick(deadline, "deadline")
                if now >= deadline:
                    raise DeadlineExceeded("deadline passed before admission",
                                           deadline=deadline, now=now)
            idem_key = request.get("idempotency_key")
            fingerprint = hashlib.sha256(canonical(
                {"tenant": tenant, "version": version,
                 "workload": request.get("workload")})).hexdigest()
            with self._lock:
                if idem_key is not None:
                    idem_key = _validate_identifier(idem_key, "idempotency_key")
                    cached = self._idem.get((tenant, idem_key))
                    if cached is not None:
                        if cached[0] != fingerprint:
                            raise IdempotencyConflict("idempotency key reused with a different request",
                                                      idempotency_key=idem_key)
                        self.telemetry.incr("idempotent_replays")
                        return {"ok": True, "result": dict(cached[1]), "trace_id": trace[0],
                                "parent_span": trace[2], "degraded": self.degraded(),
                                "idempotent_replay": True}
                self._admit_quota(tenant, version, now)
                result = self.pool.invoke(tenant=tenant, version=version, now=now)
                if idem_key is not None:
                    self._idem[(tenant, idem_key)] = (fingerprint, result)
                    while len(self._idem) > MAX_IDEMPOTENCY_ENTRIES:
                        self._idem.popitem(last=False)
            if cancel is not None and cancel.cancelled:
                # Work already ran; report it truthfully rather than pretend it did not.
                self.telemetry.incr("cancelled_after_execution")
            self.telemetry.incr("invocations.cold" if result["cold"] else "invocations.warm")
            self.telemetry.latency_ns.append(time.perf_counter_ns() - started)
            self.telemetry.log("invoke", tenant=tenant, outcome="ok", trace_id=trace[0],
                               span_id=trace[1], instance=result["instance"], cold=result["cold"],
                               workload=request.get("workload"))
            return {"ok": True, "result": result, "trace_id": trace[0],
                    "parent_span": trace[2], "degraded": self.degraded(),
                    "idempotent_replay": False}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return self._fail("invoke", exc, tenant, trace, started)

    def _admit_quota(self, tenant: str, version: str, now: int) -> None:
        quota = self.quota_for(tenant)
        owned = [i for i in self.pool.instances if i.tenant == tenant and not i.destroyed]
        if len(owned) < quota.max_instances:
            return
        if any(i.reusable_for(tenant, version, now) for i in owned):
            return  # warm path does not grow the tenant's footprint
        self.telemetry.incr("quota_rejections")
        raise QuotaExceeded("tenant instance quota reached", tenant=tenant,
                            quota=quota.max_instances)

    def drain(self, assertion: Mapping[str, Any], *, now: int, tenant: str | None = None,
              version: str | None = None) -> dict[str, Any]:
        started, trace = time.perf_counter_ns(), child_trace(None)
        try:
            principal = self.authenticator.authenticate(assertion, now)
            self._authorize(principal, CAP_DRAIN)
            destroyed = self.pool.destroy_idle(tenant=tenant, version=version)
            self.audit.append("pool.drain", subject=principal.subject, tick=now,
                              tenant=redact_tenant(tenant) if tenant else None,
                              version=version, destroyed=len(destroyed))
            return {"ok": True, "destroyed": destroyed}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return self._fail("drain", exc, tenant, trace, started)

    def emergency_disable(self, assertion: Mapping[str, Any], *, now: int,
                          reason: str) -> dict[str, Any]:
        started, trace = time.perf_counter_ns(), child_trace(None)
        try:
            principal = self.authenticator.authenticate(assertion, now)
            self._authorize(principal, CAP_DRAIN)
            if principal.kind == "service":
                raise AuthorizationDenied("emergency disable requires a human or operator",
                                          capability=CAP_DRAIN)
            self.disabled_reason = _validate_identifier(reason, "reason")
            self.audit.append("component.disable", subject=principal.subject, tick=now,
                              reason=self.disabled_reason)
            return {"ok": True}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return self._fail("disable", exc, None, trace, started)

    def enable(self, assertion: Mapping[str, Any], *, now: int) -> dict[str, Any]:
        started, trace = time.perf_counter_ns(), child_trace(None)
        try:
            principal = self.authenticator.authenticate(assertion, now)
            self._authorize(principal, CAP_DRAIN)
            if principal.kind == "service":
                raise AuthorizationDenied("re-enable requires a human or operator",
                                          capability=CAP_DRAIN)
            self.disabled_reason = None
            self.audit.append("component.enable", subject=principal.subject, tick=now)
            return {"ok": True}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return self._fail("enable", exc, None, trace, started)

    def health(self, now: int) -> dict[str, Any]:
        """Unauthenticated liveness/readiness summary; tenant-free by construction (C071)."""
        from . import __version__
        now = _validate_tick(now)
        critical_ok = all(self.dependencies.get(d, False) for d in CRITICAL_DEPENDENCIES)
        snap = self.pool.pool_snapshot(now)
        busy = sum(1 for i in snap["instances"] if i["in_flight"])
        return {
            "schema": "PK_INV31_HEALTH/1",
            "live": True,
            "ready": critical_ok and self.disabled_reason is None
                     and self.authenticator.available,
            "version": __version__,
            "disabled": self.disabled_reason is not None,
            "authenticator_keys_loaded": self.authenticator.available,
            "dependencies": dict(self.dependencies),
            "degraded": self.degraded(),
            "configuration": snap["configuration"],
            "saturation": {
                "instances": len(snap["instances"]),
                "max_instances": snap["configuration"]["max_instances"],
                "utilisation": len(snap["instances"]) / snap["configuration"]["max_instances"],
                "busy_instances": busy,
            },
            "capabilities": sorted({CAP_OBSERVE, CAP_DRAIN, CAP_CONFIG, "invoke:<tenant>"}),
            "audit_chain_ok": self.audit.verify(),
        }

    def metrics(self) -> dict[str, Any]:
        snap = self.pool.pool_snapshot(max((i.last_used_at for i in self.pool.instances),
                                           default=0))
        return {"schema": "PK_INV31_METRICS/1", "counters": dict(self.telemetry.counters),
                "latency_ns": self.telemetry.percentiles(), "pool": snap["stats"]}

    def explain(self, assertion: Mapping[str, Any], *, tenant: str, version: str,
                now: int) -> dict[str, Any]:
        """Operator explain view: why would the next invocation be warm or cold (C077)."""
        started, trace = time.perf_counter_ns(), child_trace(None)
        try:
            principal = self.authenticator.authenticate(assertion, now)
            self._authorize(principal, CAP_OBSERVE)
            tenant = _validate_identifier(tenant, "tenant")
            version = _validate_identifier(version, "version")
            candidates = []
            for inst in self.pool.instances:
                if inst.tenant != tenant:
                    continue  # never reveal other tenants' instances
                s = inst.snapshot(now)
                reasons = []
                if s["destroyed"]:
                    reasons.append("destroyed")
                if inst.version != version:
                    reasons.append("version_mismatch")
                if s["age"] < 0:
                    reasons.append("clock_rollback")
                elif s["age"] > inst.max_age:
                    reasons.append("expired")
                if s["in_flight"] >= inst.concurrency_limit:
                    reasons.append("at_concurrency_limit")
                candidates.append({"instance": s["name"], "reusable": not reasons,
                                   "rejected_because": reasons})
            quota = self.quota_for(tenant).max_instances
            owned = sum(1 for i in self.pool.instances if i.tenant == tenant)
            return {"ok": True, "tenant": redact_tenant(tenant), "version": version,
                    "predicted": "warm" if any(c["reusable"] for c in candidates) else "cold",
                    "policy": {"reuse_rule": "exact tenant and code version, age within max_age",
                               "tenant_quota": quota, "tenant_instances": owned,
                               "pool_max_instances": self.pool.max_instances},
                    "candidates": candidates}
        except (Inv31Error, RuntimeError, TypeError, ValueError) as exc:
            return self._fail("explain", exc, tenant, trace, started)


def bounded_retry(operation, *, attempts: int = 3, base_delay: float = 0.01,
                  max_delay: float = 0.2, sleep=time.sleep,
                  rng: secrets.SystemRandom | None = None) -> Any:
    """Retry an *idempotent* operation on retryable INV-31 errors only (C053).

    Full-jitter exponential backoff; non-retryable errors propagate immediately.
    ``operation`` must return a Gateway response dict.
    """
    if not isinstance(attempts, int) or not 1 <= attempts <= 10:
        raise ValueError("attempts must be 1..10")
    rng = rng or secrets.SystemRandom()
    last: dict[str, Any] | None = None
    for attempt in range(attempts):
        last = operation()
        if last.get("ok") or not last.get("error", {}).get("retryable"):
            return last
        if attempt + 1 < attempts:
            sleep(rng.uniform(0, min(max_delay, base_delay * (2 ** attempt))))
    return last


__all__ = [
    "REQUEST_SCHEMA", "SUPPORTED_REQUEST_SCHEMAS", "Principal", "HmacAuthenticator",
    "AuditLog", "Telemetry", "CancelToken", "TenantQuota", "Gateway", "bounded_retry",
    "invoke_capability", "redact_tenant", "child_trace", "CAP_OBSERVE", "CAP_DRAIN",
    "CAP_CONFIG", "CRITICAL_DEPENDENCIES", "NONCRITICAL_DEPENDENCIES",
]
