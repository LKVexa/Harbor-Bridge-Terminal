"""Boundary authentication, capability authorization and tenant scoping.

INV-68 MC-06 (C023, C024, C042-C044, C046); threat-model controls T1-T4.

The pure engine (``packing.py``) never authenticates -- it is a library.  Every
*boundary* (``service.PackingService``) calls :class:`Authorizer`:

* **Principal** -- ``kind`` is one of ``workload-scheduler`` (SCH-01),
  ``k8s-adapter`` (INV-67), ``operator``, ``node`` or ``controller``; each has a
  tenant scope (``"*"`` only for operators/controllers) and a capability set.
* **Credential** -- a compact token ``v1.<b64 claims>.<b64 HMAC-SHA256>`` signed
  by a trust root key held by the deployment's secret store (the repository
  holds only ``secretref://`` references).  Claims: ``sub``, ``kind``,
  ``tenants``, ``caps``, ``iat``, ``exp``, ``nonce``, ``kid``.  Expiry uses a
  bounded clock skew; nonces are single-use inside their validity window
  (replay protection); unknown ``kid`` or an unsigned token fails closed.
* **Capabilities** (least privilege): ``pack:submit``, ``pack:explain``,
  ``capacity:read``, ``status:read``, ``config:activate``, ``config:rollback``,
  ``control:freeze``, ``audit:read``.  :data:`KIND_CEILING` caps what each
  principal kind may ever be granted, so a scheduler token minted with
  ``config:activate`` is still refused.
* **Tenant boundary** -- a request's tenant must be inside the principal's
  scope; workloads never cross tenants because each request is packed alone
  and results carry the tenant id.

Denials raise :class:`~inv68_resource_packing.errors.PackError` with
``UNAUTHENTICATED``, ``FORBIDDEN`` or ``REPLAY_DETECTED`` and never reveal which
check failed beyond the code.  Production deployments should replace the HMAC
trust root with mTLS/SPIFFE or OIDC-issued tokens (see ``SECURITY.md``); the
interface -- ``authenticate(token) -> Principal`` -- stays the same.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from .errors import PackError

CAPABILITIES = frozenset({
    "pack:submit", "pack:explain", "capacity:read", "status:read",
    "config:activate", "config:rollback", "control:freeze", "audit:read",
})

KIND_CEILING: Mapping[str, frozenset[str]] = {
    "workload-scheduler": frozenset({"pack:submit", "pack:explain", "capacity:read", "status:read"}),
    "k8s-adapter": frozenset({"pack:submit", "capacity:read", "status:read"}),
    "node": frozenset({"status:read"}),
    "operator": frozenset({"pack:explain", "capacity:read", "status:read", "control:freeze", "audit:read",
                           "config:rollback"}),
    "controller": frozenset({"config:activate", "config:rollback", "control:freeze", "status:read"}),
}
WILDCARD_KINDS = frozenset({"operator", "controller"})
MAX_TOKEN_BYTES = 4096
MAX_TTL_S = 3600
CLOCK_SKEW_S = 30


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str
    tenants: frozenset[str]
    capabilities: frozenset[str]
    key_id: str
    expires: float

    def in_tenant(self, tenant: str) -> bool:
        return "*" in self.tenants or tenant in self.tenants


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def mint(key: bytes, *, kid: str, sub: str, kind: str, tenants: Iterable[str], caps: Iterable[str],
         ttl_s: int = 300, now: float | None = None, nonce: str | None = None) -> str:
    """Issue a token (test/bootstrap helper; production issuers are external)."""
    now = time.time() if now is None else now
    claims = {"v": 1, "sub": sub, "kind": kind, "tenants": sorted(tenants), "caps": sorted(caps),
              "iat": int(now), "exp": int(now + ttl_s), "nonce": nonce or secrets.token_hex(12), "kid": kid}
    body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
    sig = _b64(hmac.new(key, f"v1.{body}".encode(), hashlib.sha256).digest())
    return f"v1.{body}.{sig}"


@dataclass
class Authorizer:
    """Verifies tokens against trust roots and enforces capability + tenant scope."""

    keys: Mapping[str, bytes]
    clock: Callable[[], float] = time.time
    _seen: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def authenticate(self, token: object) -> Principal:
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_BYTES:
            raise PackError("UNAUTHENTICATED")
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != "v1":
            raise PackError("UNAUTHENTICATED")
        try:
            claims = json.loads(_unb64(parts[1]))
            sig = _unb64(parts[2])
        except (ValueError, TypeError):
            raise PackError("UNAUTHENTICATED") from None
        if not isinstance(claims, dict):
            raise PackError("UNAUTHENTICATED")
        key = self.keys.get(str(claims.get("kid")))
        if key is None:
            raise PackError("UNAUTHENTICATED")
        want = hmac.new(key, f"v1.{parts[1]}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(want, sig):
            raise PackError("UNAUTHENTICATED")
        now = self.clock()
        try:
            iat, exp = float(claims["iat"]), float(claims["exp"])
            kind, sub, nonce = str(claims["kind"]), str(claims["sub"]), str(claims["nonce"])
            tenants = frozenset(str(t) for t in claims["tenants"])
            caps = frozenset(str(c) for c in claims["caps"])
        except (KeyError, TypeError, ValueError):
            raise PackError("UNAUTHENTICATED") from None
        if exp - iat > MAX_TTL_S or now > exp + CLOCK_SKEW_S or now + CLOCK_SKEW_S < iat:
            raise PackError("UNAUTHENTICATED")
        if kind not in KIND_CEILING or not caps <= CAPABILITIES:
            raise PackError("UNAUTHENTICATED")
        if "*" in tenants and kind not in WILDCARD_KINDS:
            raise PackError("UNAUTHENTICATED")
        with self._lock:
            for n, until in list(self._seen.items()):
                if until < now:
                    del self._seen[n]
            if nonce in self._seen:
                raise PackError("REPLAY_DETECTED")
            self._seen[nonce] = exp + CLOCK_SKEW_S
        return Principal(sub, kind, tenants, caps & KIND_CEILING[kind], str(claims["kid"]), exp)

    @staticmethod
    def require(principal: Principal, capability: str, tenant: str | None = None) -> None:
        if capability not in CAPABILITIES:
            raise ValueError(f"unknown capability {capability!r}")
        if capability not in principal.capabilities:
            raise PackError("FORBIDDEN", details={"capability": capability})
        if tenant is not None and not principal.in_tenant(tenant):
            raise PackError("FORBIDDEN", details={"tenant_scope": "outside"})
