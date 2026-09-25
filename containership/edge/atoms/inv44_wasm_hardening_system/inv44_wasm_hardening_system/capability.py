"""Identity and capability enforcement for INV-44 (missing component 12).

* ``Principal`` — an authenticated actor. It can only be produced by an
  ``Authenticator`` (HMAC credential check); a bare string is refused wherever
  an identity is required. Service principals are marked as such.
* ``CapabilityToken`` — HMAC-sealed grant of explicit operations and host
  imports to one principal, one tenant, until an expiry; revocable by id.
* ``check_imports`` — ambient-authority elimination (C043): a module may only
  import host functions its token names. Everything else is refused, including
  all WASI filesystem/network/clock/random entry points unless granted.

Fail-closed on dependency loss (C048): when the clock or the revocation list is
unavailable the authorizer refuses with WH-DEPENDENCY-UNAVAILABLE instead of
assuming the token is still good.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Final, Iterable

from .errors import HardeningError

OPERATIONS: Final[frozenset[str]] = frozenset({
    "instantiate", "configure", "read_metrics", "read_audit", "issue_receipt",
})
_PRINCIPAL_SEAL: Final[object] = object()


class AuthenticationFailed(HardeningError):
    code = "WH-AUTHN-FAILED"


class AuthorizationDenied(HardeningError):
    code = "WH-AUTHZ-DENIED"


class CapabilityExpired(HardeningError):
    code = "WH-CAPABILITY-EXPIRED"


class AmbientImport(HardeningError):
    code = "WH-AMBIENT-IMPORT"


class DependencyUnavailable(HardeningError):
    code = "WH-DEPENDENCY-UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant: str
    is_service: bool
    _seal: object = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self._seal is not _PRINCIPAL_SEAL:
            raise AuthenticationFailed("Principal must be produced by an Authenticator")


class Authenticator:
    """Verifies HMAC credentials: mac = HMAC(key, subject|tenant|kind)."""

    def __init__(self, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("authenticator key must be >= 32 bytes")
        self._key = key

    def credential(self, subject: str, tenant: str, *, service: bool) -> str:
        msg = f"{subject}|{tenant}|{'svc' if service else 'human'}".encode()
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()

    def authenticate(self, subject: str, tenant: str, *, service: bool, credential: str) -> Principal:
        if not isinstance(credential, str) or not hmac.compare_digest(
                self.credential(subject, tenant, service=service), credential):
            raise AuthenticationFailed("credential rejected", subject=subject)
        return Principal(subject, tenant, service, _PRINCIPAL_SEAL)


def _canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True, slots=True)
class CapabilityToken:
    token_id: str
    subject: str
    tenant: str
    operations: frozenset[str]
    imports: frozenset[str]          # "module.name" host imports granted
    expires_at: int
    mac: str

    def body(self) -> dict:
        return {"token_id": self.token_id, "subject": self.subject, "tenant": self.tenant,
                "operations": sorted(self.operations), "imports": sorted(self.imports),
                "expires_at": self.expires_at}


class Authorizer:
    def __init__(self, key: bytes, *, clock: Callable[[], float] = time.time,
                 revoked: Callable[[], Iterable[str]] | None = None) -> None:
        if len(key) < 32:
            raise ValueError("authorizer key must be >= 32 bytes")
        self._key = key
        self._clock = clock
        self._revoked_source = revoked or (lambda: ())

    def grant(self, principal: Principal, *, token_id: str, operations: Iterable[str],
              imports: Iterable[str] = (), ttl_s: int = 900) -> CapabilityToken:
        if not isinstance(principal, Principal):
            raise AuthenticationFailed("grant requires an authenticated Principal")
        ops = frozenset(operations)
        unknown = ops - OPERATIONS
        if unknown or not ops:
            raise AuthorizationDenied("unknown or empty operation set", unknown=sorted(unknown))
        if not 0 < ttl_s <= 86_400:
            raise AuthorizationDenied("ttl must be within 1..86400 seconds")
        tok = CapabilityToken(token_id, principal.subject, principal.tenant, ops,
                              frozenset(imports), int(self._clock()) + ttl_s, "")
        return CapabilityToken(**{**_as_kwargs(tok), "mac": self._mac(tok)})

    def _mac(self, tok: CapabilityToken) -> str:
        return hmac.new(self._key, _canon(tok.body()), hashlib.sha256).hexdigest()

    def authorize(self, principal: Principal, token: CapabilityToken, operation: str) -> None:
        if not isinstance(principal, Principal):
            raise AuthenticationFailed("authorize requires an authenticated Principal")
        if not isinstance(token, CapabilityToken) or not hmac.compare_digest(self._mac(token), token.mac):
            raise AuthorizationDenied("capability token seal invalid")
        if token.subject != principal.subject or token.tenant != principal.tenant:
            raise AuthorizationDenied("token not issued to this principal")
        try:
            now = self._clock()
            revoked = set(self._revoked_source())
        except Exception as exc:  # any trust-dependency failure fails closed
            raise DependencyUnavailable("clock or revocation source unavailable") from exc
        if token.token_id in revoked:
            raise CapabilityExpired("token revoked", token_id=token.token_id)
        if now >= token.expires_at:
            raise CapabilityExpired("token expired", token_id=token.token_id)
        if operation not in token.operations:
            raise AuthorizationDenied("operation not granted", operation=operation)


def _as_kwargs(tok: CapabilityToken) -> dict:
    return {f: getattr(tok, f) for f in CapabilityToken.__slots__}


def check_imports(imports: Iterable[tuple[str, str, str]], token: CapabilityToken) -> None:
    """Refuse any function import not explicitly granted (no ambient authority)."""
    ungranted = sorted(f"{m}.{n}" for m, n, kind in imports
                       if kind == "func" and f"{m}.{n}" not in token.imports)
    if ungranted:
        raise AmbientImport("module imports ungranted host functions", imports=ungranted)
