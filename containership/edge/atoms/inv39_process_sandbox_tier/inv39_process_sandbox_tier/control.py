"""Control-plane primitives.

MC-013 authentication  : HMAC-signed bearer tokens bound to principal, audience, expiry.
MC-014 authorization   : role -> capability map; tenant-scoped; deny by default.
MC-015 idempotency     : request-key cache; same key + different body -> E_CONFLICT.
MC-015/058 retry       : bounded exponential backoff with full jitter, only for retryable codes.
MC-008/018/059 admission: global concurrency, per-tenant quota, bounded queue, circuit breaker.
MC-063 ownership       : fenced leases (monotonic fencing token) -> stale controllers refused.
MC-064 quarantine      : authorized, audited freeze/kill switch per workload/tenant/node.
MC-017 negotiation     : pick highest mutually supported schema version or refuse.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import SandboxError

# ---------------------------------------------------------------- authn (MC-013)
TOKEN_MAX_TTL_S = 3600


def issue_token(key: bytes, principal: str, audience: str, ttl_s: int, now: float | None = None) -> str:
    now = time.time() if now is None else now
    body = json.dumps({"sub": principal, "aud": audience, "exp": int(now + min(ttl_s, TOKEN_MAX_TTL_S))},
                      sort_keys=True, separators=(",", ":"))
    mac = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    return body.encode().hex() + "." + mac


def authenticate(keys: dict[str, bytes], token: str, audience: str, now: float | None = None) -> str:
    """Return the authenticated principal or raise E_UNAUTHENTICATED."""
    now = time.time() if now is None else now
    if not isinstance(token, str) or len(token) > 4096 or token.count(".") != 1:
        raise SandboxError("E_UNAUTHENTICATED", "malformed token")
    hexbody, mac = token.split(".")
    try:
        body = bytes.fromhex(hexbody).decode()
        claims = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise SandboxError("E_UNAUTHENTICATED", "malformed token") from None
    key = keys.get(claims.get("sub", ""))
    if key is None:
        raise SandboxError("E_UNAUTHENTICATED", "unknown principal")
    if not hmac.compare_digest(hmac.new(key, body.encode(), hashlib.sha256).hexdigest(), mac):
        raise SandboxError("E_UNAUTHENTICATED", "bad token signature")
    if claims.get("aud") != audience:
        raise SandboxError("E_UNAUTHENTICATED", "token audience mismatch")
    if not isinstance(claims.get("exp"), int) or claims["exp"] < now:
        raise SandboxError("E_UNAUTHENTICATED", "token expired")
    return claims["sub"]


# ---------------------------------------------------------------- authz (MC-014)
OPERATIONS = ("create", "update", "launch", "inspect", "terminate", "quarantine", "config.activate")
ROLES = {
    "tenant-operator": {"create", "launch", "inspect", "terminate"},
    "tenant-viewer": {"inspect"},
    "policy-admin": {"update", "config.activate", "inspect"},
    "security-responder": {"quarantine", "terminate", "inspect"},
}


@dataclass
class Authorizer:
    grants: dict[str, set[tuple[str, str]]] = field(default_factory=dict)  # principal -> {(role, tenant|*)}

    def grant(self, principal: str, role: str, tenant: str) -> None:
        if role not in ROLES:
            raise SandboxError("E_PROFILE_INVALID", f"unknown role {role!r}")
        self.grants.setdefault(principal, set()).add((role, tenant))

    def check(self, principal: str, op: str, tenant: str) -> None:
        if op not in OPERATIONS:
            raise SandboxError("E_UNAUTHORIZED", f"unknown operation {op!r}")
        for role, scope in self.grants.get(principal, ()):
            if op in ROLES[role] and scope in (tenant, "*"):
                return
        raise SandboxError("E_UNAUTHORIZED", f"{principal} may not {op} in tenant {tenant}")


# ---------------------------------------------------------------- idempotency (MC-015)
class IdempotencyCache:
    def __init__(self, max_entries: int = 10_000, ttl_s: float = 3600):
        self.max_entries, self.ttl_s = max_entries, ttl_s
        self._d: dict[str, tuple[float, str, Any]] = {}
        self._lock = threading.Lock()

    def run(self, key: str, request: Any, fn: Callable[[], Any]) -> Any:
        rd = hashlib.sha256(json.dumps(request, sort_keys=True, default=str).encode()).hexdigest()
        now = time.monotonic()
        with self._lock:
            hit = self._d.get(key)
            if hit and now - hit[0] < self.ttl_s:
                if hit[1] != rd:
                    raise SandboxError("E_CONFLICT", "idempotency key reused with a different request")
                return hit[2]
        result = fn()
        with self._lock:
            if len(self._d) >= self.max_entries:
                for k in sorted(self._d, key=lambda k: self._d[k][0])[: self.max_entries // 10 or 1]:
                    del self._d[k]
            self._d[key] = (now, rd, result)
        return result


def retry(fn: Callable[[], Any], *, attempts: int = 4, base_s: float = 0.05, cap_s: float = 2.0,
          deadline_s: float = 10.0, sleep=time.sleep, rng=random.random) -> Any:
    """MC-058: bounded, jittered retry; only codes marked retryable are retried."""
    attempts = max(1, min(attempts, 10))
    end = time.monotonic() + deadline_s
    for i in range(attempts):
        try:
            return fn()
        except SandboxError as e:
            if not e.retryable or i == attempts - 1:
                raise
            delay = rng() * min(cap_s, base_s * (2 ** i))
            if time.monotonic() + delay > end:
                raise SandboxError("E_TIMEOUT", "retry deadline exhausted") from e
            sleep(delay)
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- admission (MC-008/018/059)
@dataclass
class Limits:
    max_concurrent: int = 256
    max_per_tenant: int = 32
    max_queue: int = 64
    max_payload_bytes: int = 64 * 1024
    breaker_failures: int = 5
    breaker_reset_s: float = 30.0


class Admission:
    def __init__(self, limits: Limits | None = None, clock=time.monotonic):
        self.limits = limits or Limits()
        self.clock = clock
        self.active: dict[str, int] = {}
        self.total = 0
        self.failures = 0
        self.opened_at: float | None = None
        self._lock = threading.Lock()

    def check_payload(self, raw: bytes) -> None:
        if len(raw) > self.limits.max_payload_bytes:
            raise SandboxError("E_LIMIT_EXCEEDED", f"payload {len(raw)}B > {self.limits.max_payload_bytes}B")

    def acquire(self, tenant: str) -> None:
        with self._lock:
            if self.opened_at is not None:
                if self.clock() - self.opened_at < self.limits.breaker_reset_s:
                    raise SandboxError("E_CIRCUIT_OPEN", "backend circuit open")
                self.opened_at, self.failures = None, self.limits.breaker_failures - 1  # half-open
            if self.total >= self.limits.max_concurrent:
                raise SandboxError("E_OVERLOADED", "node concurrency ceiling reached")
            if self.active.get(tenant, 0) >= self.limits.max_per_tenant:
                raise SandboxError("E_QUOTA_EXCEEDED", f"tenant {tenant} at quota")
            self.active[tenant] = self.active.get(tenant, 0) + 1
            self.total += 1

    def release(self, tenant: str, ok: bool) -> None:
        with self._lock:
            if self.active.get(tenant, 0) > 0:
                self.active[tenant] -= 1
                self.total -= 1
            if ok:
                self.failures = 0
            else:
                self.failures += 1
                if self.failures >= self.limits.breaker_failures:
                    self.opened_at = self.clock()


# ---------------------------------------------------------------- leases (MC-063)
class LeaseTable:
    def __init__(self, ttl_s: float = 15.0, clock=time.monotonic):
        self.ttl_s, self.clock = ttl_s, clock
        self._leases: dict[str, tuple[str, int, float]] = {}
        self._fence = 0
        self._lock = threading.Lock()

    def acquire(self, resource: str, owner: str) -> int:
        with self._lock:
            cur = self._leases.get(resource)
            if cur and cur[0] != owner and self.clock() < cur[2]:
                raise SandboxError("E_OWNERSHIP_LOST", f"{resource} owned by {cur[0]}")
            self._fence += 1
            self._leases[resource] = (owner, self._fence, self.clock() + self.ttl_s)
            return self._fence

    def check(self, resource: str, owner: str, fence: int) -> None:
        with self._lock:
            cur = self._leases.get(resource)
            if not cur or cur[0] != owner or cur[1] != fence or self.clock() >= cur[2]:
                raise SandboxError("E_OWNERSHIP_LOST", f"stale lease for {resource}")


# ---------------------------------------------------------------- quarantine (MC-064)
class Quarantine:
    def __init__(self, authz: Authorizer, audit):
        self.authz, self.audit = authz, audit
        self.blocked: dict[str, str] = {}

    def set(self, principal: str, tenant: str, target: str, reason: str) -> None:
        self.authz.check(principal, "quarantine", tenant)
        self.blocked[target] = reason
        self.audit.append("quarantine", {"by": principal, "tenant": tenant, "target": target, "reason": reason})

    def lift(self, principal: str, tenant: str, target: str) -> None:
        self.authz.check(principal, "quarantine", tenant)
        self.blocked.pop(target, None)
        self.audit.append("quarantine.lift", {"by": principal, "tenant": tenant, "target": target})

    def check(self, *targets: str) -> None:
        for t in targets:
            if t in self.blocked:
                raise SandboxError("E_QUARANTINED", f"{t} is quarantined: {self.blocked[t]}")


# ---------------------------------------------------------------- versions (MC-017)
SUPPORTED = {"PK_SANDBOX_PROFILE": (1,), "PK_SANDBOX_APPLIED": (1, 2), "PK_SANDBOX_ERROR": (1,)}


def negotiate(family: str, peer_versions) -> int:
    ours = set(SUPPORTED.get(family, ()))
    common = ours & {int(v) for v in peer_versions}
    if not common:
        raise SandboxError("E_VERSION_UNSUPPORTED", f"{family}: ours {sorted(ours)}, peer {sorted(peer_versions)}")
    return max(common)
