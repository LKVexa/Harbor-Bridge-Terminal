"""Capability decision contract and guarded provider integration (PK_CAPABILITY/1).

GAP-004. The chainer never *decides* authorization; it asks an authoritative
provider (INV-13 system interface in production) through
:class:`GuardedProvider`, which enforces:

* a versioned request/decision contract with a decision correlation id;
* fail-closed on timeout, exception, malformed decision, unknown verdict,
  version mismatch or stale policy revision;
* a bounded decision cache (TTL, max entries, keyed on every dimension), with no
  negative caching unless configured. Revocation: immediate when the provider
  exposes a live ``revision`` (checked on every cache hit) or when
  :meth:`invalidate` is called from a revocation event; otherwise bounded by TTL.

:class:`CompatLocalProvider` reproduces the 4.2 behaviour (same-tenant local
only) and is *refused* when the chainer runs in ``production`` mode.
"""
from __future__ import annotations

import concurrent.futures as cf
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from .errors import ProviderUnavailable

CAPABILITY_SCHEMA = "PK_CAPABILITY/1"


@dataclass(frozen=True)
class CapabilityRequest:
    principal: str
    tenant: str
    caller: Optional[str]
    callee: str
    operation: str
    capabilities: frozenset
    topology: str  # "local" | "remote"
    depth: int
    correlation_id: str
    schema: str = CAPABILITY_SCHEMA

    def cache_key(self) -> tuple:
        return (self.principal, self.tenant, self.caller, self.callee, self.operation,
                tuple(sorted(self.capabilities)), self.topology)


@dataclass(frozen=True)
class CapabilityDecision:
    allow: bool
    policy_revision: int
    reason: str
    correlation_id: str
    schema: str = CAPABILITY_SCHEMA


class CapabilityProvider(Protocol):
    authoritative: bool

    def decide(self, request: CapabilityRequest) -> CapabilityDecision: ...


class CompatLocalProvider:
    """4.2-compatible fallback. NOT an authority; refused in production mode."""

    authoritative = False

    def decide(self, request: CapabilityRequest) -> CapabilityDecision:
        return CapabilityDecision(True, 0, "compat_same_tenant", request.correlation_id)


class StaticPolicyProvider:
    """Deterministic authoritative provider for tests / single-host deployments.

    Grants iff (tenant, callee, operation) is in the grant set AND the
    principal holds every required capability for that callee.
    """

    authoritative = True

    def __init__(self, grants=(), required=None, revision: int = 1) -> None:
        self._grants = set(grants)
        self._required = dict(required or {})
        self.revision = revision
        self._lock = threading.Lock()

    def grant(self, tenant, callee, operation="invoke"):
        with self._lock:
            self._grants.add((tenant, callee, operation)); self.revision += 1

    def revoke(self, tenant, callee, operation="invoke"):
        with self._lock:
            self._grants.discard((tenant, callee, operation)); self.revision += 1

    def decide(self, request: CapabilityRequest) -> CapabilityDecision:
        with self._lock:
            ok = (request.tenant, request.callee, request.operation) in self._grants
            need = self._required.get(request.callee, frozenset())
            ok = ok and set(need) <= set(request.capabilities)
            return CapabilityDecision(ok, self.revision, "granted" if ok else "no_grant",
                                      request.correlation_id)


_EXECUTOR = cf.ThreadPoolExecutor(max_workers=8, thread_name_prefix="inv21-policy")


class GuardedProvider:
    """Fail-closed wrapper around an authoritative provider."""

    def __init__(self, provider: CapabilityProvider, *, timeout_s: float = 0.25,
                 cache_ttl_s: float = 0.0, cache_max: int = 4096,
                 min_policy_revision: int = 0, cache_denials: bool = False) -> None:
        if not hasattr(provider, "decide"):
            raise TypeError("provider must implement decide()")
        if not 0 < timeout_s <= 30:
            raise ValueError("timeout_s out of range")
        if not 0 <= cache_ttl_s <= 300 or not 1 <= cache_max <= 1_000_000:
            raise ValueError("cache bounds out of range")
        self.provider = provider
        self.timeout_s = timeout_s
        self.cache_ttl_s = cache_ttl_s
        self.cache_max = cache_max
        self.min_policy_revision = min_policy_revision
        self.cache_denials = cache_denials
        self._cache: "OrderedDict[tuple, tuple[float, CapabilityDecision]]" = OrderedDict()
        self._lock = threading.Lock()
        self.stats = {"decisions": 0, "cache_hits": 0, "failures": 0, "denials": 0}
        self.last_error: Optional[str] = None

    @property
    def authoritative(self) -> bool:
        return bool(getattr(self.provider, "authoritative", False))

    def invalidate(self, *, min_policy_revision: Optional[int] = None) -> None:
        with self._lock:
            self._cache.clear()
            if min_policy_revision is not None:
                self.min_policy_revision = max(self.min_policy_revision, min_policy_revision)

    def _fail(self, why: str, req: CapabilityRequest):
        with self._lock:
            self.stats["failures"] += 1
            self.last_error = why
        raise ProviderUnavailable("capability provider unavailable; failing closed",
                                  reason=why, trace_id=req.correlation_id)

    def decide(self, req: CapabilityRequest) -> CapabilityDecision:
        key = req.cache_key()
        now = time.monotonic()
        if self.cache_ttl_s:
            with self._lock:
                hit = self._cache.get(key)
                # a provider that exposes its live revision makes revocation immediate
                live = getattr(self.provider, "revision", None)
                floor = max(self.min_policy_revision, live if isinstance(live, int) else 0)
                if hit and hit[0] > now and hit[1].policy_revision >= floor:
                    self._cache.move_to_end(key)
                    self.stats["cache_hits"] += 1
                    return hit[1]
        fut = _EXECUTOR.submit(self.provider.decide, req)
        try:
            d = fut.result(timeout=self.timeout_s)
        except cf.TimeoutError:
            fut.cancel()
            self._fail("timeout", req)
        except Exception as exc:  # provider fault -> closed
            self._fail("error:" + type(exc).__name__, req)
        if not isinstance(d, CapabilityDecision) or not isinstance(d.allow, bool):
            self._fail("malformed", req)
        if d.schema != CAPABILITY_SCHEMA:
            self._fail("version_mismatch", req)
        if d.correlation_id != req.correlation_id:
            self._fail("correlation_mismatch", req)
        if d.policy_revision < self.min_policy_revision:
            self._fail("stale_policy", req)
        with self._lock:
            self.stats["decisions"] += 1
            if not d.allow:
                self.stats["denials"] += 1
            if self.cache_ttl_s and (d.allow or self.cache_denials):
                self._cache[key] = (now + self.cache_ttl_s, d)
                while len(self._cache) > self.cache_max:
                    self._cache.popitem(last=False)
        return d


def new_correlation_id() -> str:
    return "dc-" + secrets.token_hex(8)
