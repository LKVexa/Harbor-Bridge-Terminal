"""Boundary authentication and attestation interfaces (MC-03, MC-64).

PLN-07 does not *own* identity (GAP-06 does); it owns the boundary contract
that every caller of issue/revoke/verify must satisfy.  This module defines:

* ``Principal`` - the authenticated caller, as asserted by an authenticator.
* ``Authenticator`` - protocol for GAP-06 adapters (mTLS, workload identity,
  hardware attestation).  ``authenticate`` must fail closed.
* ``StaticTokenAuthenticator`` - HMAC bearer-token reference adapter for tests
  and single-host deployments.
* ``AttestationPolicy`` - minimum evidence a principal must carry to be
  issued grants for a given environment (e.g. prod requires ``tpm``).
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Mapping, Protocol

from .grants import SecurityPlaneError


class AuthenticationFailed(SecurityPlaneError):
    code = "auth.failed"


class AttestationInsufficient(SecurityPlaneError):
    code = "auth.attestation"


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    roles: frozenset[str] = frozenset()
    attestation: frozenset[str] = frozenset()  # e.g. {"tpm", "sev-snp"}
    authn_method: str = "unknown"


class Authenticator(Protocol):
    def authenticate(self, credentials: Mapping[str, str]) -> Principal: ...


@dataclass
class StaticTokenAuthenticator:
    """Reference authenticator: tokens are HMAC-SHA256(secret, subject|tenant)."""

    secret: bytes
    directory: dict[str, Principal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.secret) < 32:
            raise ValueError("authenticator secret must be at least 32 bytes")

    def token_for(self, principal: Principal) -> str:
        key = f"{principal.subject}|{principal.tenant}"
        self.directory[key] = principal
        return hmac.new(self.secret, key.encode(), hashlib.sha256).hexdigest()

    def authenticate(self, credentials: Mapping[str, str]) -> Principal:
        subject = credentials.get("subject", "")
        tenant = credentials.get("tenant", "")
        token = credentials.get("token", "")
        key = f"{subject}|{tenant}"
        expected = hmac.new(self.secret, key.encode(), hashlib.sha256).hexdigest()
        principal = self.directory.get(key)
        if principal is None or not hmac.compare_digest(expected, str(token)):
            # uniform failure: do not reveal which part was wrong
            raise AuthenticationFailed("authentication failed")
        return principal


@dataclass(frozen=True)
class AttestationPolicy:
    required_by_environment: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def check(self, principal: Principal, environment: str | None) -> None:
        need = self.required_by_environment.get(environment or "", frozenset())
        missing = need - principal.attestation
        if missing:
            raise AttestationInsufficient(
                "principal lacks required attestation evidence",
                details={"missing": sorted(missing), "environment": environment},
            )
