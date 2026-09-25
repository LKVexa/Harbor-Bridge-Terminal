"""Authentication, authorization and quota/fairness (MC-010, MC-011, MC-012, MC-031).

SPDX-License-Identifier: NOASSERTION

Callers authenticate with a bearer credential ``<principal_id>.<unix_ts>.<nonce>.<hmac>``
signed with a per-principal secret held by a ``SecretSource``.  Secrets never
appear in logs, errors, or ``repr``.  This is a reference mechanism; binding it
to the operator's real IdP/KMS is an integration step (governance/BLOCKERS.json).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol


class AuthError(PermissionError):
    code = "UNAUTHENTICATED"


class Forbidden(PermissionError):
    code = "FORBIDDEN"


class QuotaExceeded(RuntimeError):
    code = "QUOTA_EXCEEDED"
    retryable = True


class SecretSource(Protocol):
    def get(self, principal_id: str) -> bytes | None: ...


class _Secret(bytes):
    def __repr__(self) -> str:  # never print secret material
        return "<redacted>"


class EnvSecretSource:
    """Reads ``INV34_SECRET_<PRINCIPAL>`` (hex). Rotation = set ``..._NEXT``; both accepted."""

    def __init__(self, environ: dict[str, str] | None = None) -> None:
        self._env = os.environ if environ is None else environ

    def get_all(self, principal_id: str) -> list[bytes]:
        key = "INV34_SECRET_" + principal_id.upper().replace("-", "_")
        out = []
        for name in (key, key + "_NEXT"):
            v = self._env.get(name)
            if v:
                out.append(_Secret(bytes.fromhex(v)))
        return out

    def get(self, principal_id: str) -> bytes | None:
        a = self.get_all(principal_id)
        return a[0] if a else None


@dataclass(frozen=True)
class Principal:
    principal_id: str
    kind: str                      # "caller" | "node" | "adapter" | "observer" | "operator"
    tenant: str | None = None


def mint_token(principal_id: str, secret: bytes, now: float | None = None, nonce: str | None = None) -> str:
    ts = str(int(now if now is not None else time.time()))
    nonce = nonce or os.urandom(8).hex()
    mac = hmac.new(secret, f"{principal_id}.{ts}.{nonce}".encode(), hashlib.sha256).hexdigest()
    return f"{principal_id}.{ts}.{nonce}.{mac}"


class Authenticator:
    def __init__(self, directory: dict[str, Principal], secrets: EnvSecretSource,
                 max_skew_s: float = 300.0, clock: Callable[[], float] = time.time) -> None:
        self._dir, self._secrets, self._skew, self._clock = directory, secrets, max_skew_s, clock
        self._nonces: dict[str, float] = {}
        self._lock = threading.Lock()

    def authenticate(self, token: str | None) -> Principal:
        if not token or not isinstance(token, str) or len(token) > 512:
            raise AuthError("missing credential")
        parts = token.split(".")
        if len(parts) != 4:
            raise AuthError("malformed credential")
        pid, ts, nonce, mac = parts
        principal = self._dir.get(pid)
        secrets = self._secrets.get_all(pid) if principal else []
        if not principal or not secrets:
            raise AuthError("unknown principal")
        msg = f"{pid}.{ts}.{nonce}".encode()
        if not any(hmac.compare_digest(mac, hmac.new(s, msg, hashlib.sha256).hexdigest()) for s in secrets):
            raise AuthError("bad signature")
        if not ts.isdigit() or abs(self._clock() - int(ts)) > self._skew:
            raise AuthError("credential outside validity window")
        with self._lock:
            now = self._clock()
            for n, exp in list(self._nonces.items()):
                if exp < now:
                    del self._nonces[n]
            if nonce in self._nonces:
                raise AuthError("credential replayed")
            self._nonces[nonce] = now + 2 * self._skew
        return principal


@dataclass
class VmBinding:
    vm_id: str
    tenant: str
    workload: str
    site: str


@dataclass
class CapabilityPolicy:
    """Least-privilege grants: (principal, action) -> set of tenants (or VM ids) it covers."""
    grants: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    ACTIONS = ("cpu.expand", "cpu.status", "cpu.observe", "ops.disable", "ops.enable",
               "ops.config", "ops.explain")

    def grant(self, principal_id: str, action: str, scope: str) -> None:
        if action not in self.ACTIONS:
            raise ValueError(f"unknown action {action}")
        self.grants.setdefault((principal_id, action), set()).add(scope)

    def authorize(self, principal: Principal, action: str, vm: VmBinding) -> None:
        scopes = self.grants.get((principal.principal_id, action), set())
        if principal.kind == "caller" and principal.tenant and principal.tenant != vm.tenant:
            raise Forbidden("cross-tenant access denied")
        if vm.vm_id in scopes or f"tenant:{vm.tenant}" in scopes:
            return
        raise Forbidden(f"{principal.principal_id} lacks {action} on {vm.vm_id}")


class QuotaService:
    """Tenant / site / fleet vCPU ceilings plus weighted fair share of site headroom."""

    def __init__(self, tenant_limits: dict[str, int], site_limits: dict[str, int], fleet_limit: int,
                 tenant_weights: dict[str, float] | None = None) -> None:
        self.tenant_limits, self.site_limits, self.fleet_limit = tenant_limits, site_limits, fleet_limit
        self.weights = tenant_weights or {}
        self.usage: dict[str, int] = {}          # vm_id -> committed desired vcpus
        self.vm: dict[str, VmBinding] = {}
        self._lock = threading.Lock()

    def register(self, vm: VmBinding, desired: int) -> None:
        with self._lock:
            self.vm[vm.vm_id], self.usage[vm.vm_id] = vm, desired

    def _sum(self, pred) -> int:
        return sum(u for v, u in self.usage.items() if pred(self.vm[v]))

    def reserve(self, vm_id: str, new_desired: int) -> None:
        with self._lock:
            vm = self.vm[vm_id]
            delta = new_desired - self.usage[vm_id]
            if delta <= 0:
                return
            tenant = self._sum(lambda b: b.tenant == vm.tenant) + delta
            site = self._sum(lambda b: b.site == vm.site) + delta
            fleet = sum(self.usage.values()) + delta
            if vm.tenant not in self.tenant_limits or vm.site not in self.site_limits:
                raise QuotaExceeded("no quota configured for tenant/site (fail closed)")
            if tenant > self.tenant_limits[vm.tenant]:
                raise QuotaExceeded(f"tenant {vm.tenant} quota {self.tenant_limits[vm.tenant]} exceeded")
            if site > self.site_limits[vm.site]:
                raise QuotaExceeded(f"site {vm.site} ceiling exceeded")
            if fleet > self.fleet_limit:
                raise QuotaExceeded("fleet ceiling exceeded")
            share = self.fair_share(vm.site).get(vm.tenant)
            tenants_at_site = {b.tenant for b in self.vm.values() if b.site == vm.site}
            if share is not None and len(tenants_at_site) > 1:
                used_at_site = self._sum(lambda b: b.tenant == vm.tenant and b.site == vm.site) + delta
                if used_at_site > share:
                    raise QuotaExceeded(f"tenant {vm.tenant} over weighted fair share {share} at {vm.site}")
            self.usage[vm_id] = new_desired

    def fair_share(self, site: str) -> dict[str, int]:
        tenants = sorted({b.tenant for b in self.vm.values() if b.site == site})
        total_w = sum(self.weights.get(t, 1.0) for t in tenants) or 1.0
        cap = self.site_limits.get(site, 0)
        return {t: int(cap * self.weights.get(t, 1.0) / total_w) for t in tenants}
