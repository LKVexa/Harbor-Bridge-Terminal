"""Authentication, capability authorization, artifact trust, and key custody.

MC-010  pluggable authenticators; fail-closed when the trust dependency is
        unavailable (``PLN01-E0010``).  A bundled HMAC bearer-token
        authenticator gives a working, testable default.
MC-011  capability model: every operation needs an explicit capability bound
        to a tenant/environment scope; default deny.
MC-020  artifact digest pinning, HMAC/ed25519-style signature hook, signer
        allowlist, approved-version policy, and provenance requirements.
MC-021  ``KeyProvider`` interface with versioned keys and rotation; the local
        provider supplies integrity (HMAC) keys.  At-rest *encryption* needs an
        external KMS/crypto library and is represented by the provider
        interface only (see governance/WAIVERS.json W-003).
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Protocol

from .errors import (ArtifactVerificationError, AuthenticationError, AuthorizationError,
                     TrustUnavailableError)

CAPABILITIES = frozenset({
    "intent:declare", "intent:retract", "intent:read", "intent:plan", "intent:report",
    "intent:rollback", "intent:transaction", "intent:admin",
})


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str                       # "human" | "service" | "reporter" | "peer"
    grants: tuple[tuple[str, str], ...] = ()   # (capability, scope)  scope: "*", "t", "t/env"
    attested: bool = False

    def allows(self, capability: str, tenant: str, environment: str) -> bool:
        scopes = {"*", tenant, f"{tenant}/{environment}"}
        return any(c in (capability, "intent:admin") and s in scopes for c, s in self.grants)


class Authenticator(Protocol):
    def authenticate(self, credential: str) -> Principal: ...


class KeyProvider:
    """Versioned symmetric keys with rotation; replace with a KMS adapter in production."""

    def __init__(self, initial: bytes | None = None, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._keys: dict[int, bytes] = {}
        self._retired: dict[int, float] = {}
        self.active_version = 0
        self.available = True
        self.rotate(initial)

    def rotate(self, material: bytes | None = None) -> int:
        self.active_version += 1
        self._keys[self.active_version] = material or os.urandom(32)
        if self.active_version > 1:
            self._retired[self.active_version - 1] = self._clock()
        return self.active_version

    def destroy(self, version: int) -> None:
        if version == self.active_version:
            raise ValueError("cannot destroy the active key")
        self._keys.pop(version, None)

    def key(self, version: int | None = None) -> tuple[int, bytes]:
        if not self.available:
            raise TrustUnavailableError("key service unavailable")
        v = self.active_version if version is None else version
        if v not in self._keys:
            raise AuthenticationError(f"unknown or destroyed key version {v}")
        return v, self._keys[v]

    def mac(self, payload: bytes, version: int | None = None) -> str:
        v, k = self.key(version)
        return f"v{v}:{hmac.new(k, payload, sha256).hexdigest()}"

    def verify_mac(self, payload: bytes, tag: str) -> bool:
        try:
            ver, digest = tag.split(":", 1)
            _, k = self.key(int(ver.lstrip("v")))
        except (ValueError, AuthenticationError):
            return False
        return hmac.compare_digest(digest, hmac.new(k, payload, sha256).hexdigest())


class HmacTokenAuthenticator:
    """Bearer tokens ``base64(json claims).mac`` signed by a KeyProvider."""

    def __init__(self, keys: KeyProvider, *, clock: Callable[[], float] = time.time, max_ttl: float = 3600) -> None:
        self.keys, self._clock, self.max_ttl = keys, clock, max_ttl
        self.revoked: set[str] = set()

    def issue(self, subject: str, kind: str, grants: Sequence[tuple[str, str]], *, ttl: float = 900,
              attested: bool = False) -> str:
        for cap, _ in grants:
            if cap not in CAPABILITIES:
                raise ValueError(f"unknown capability {cap}")
        claims = {"sub": subject, "kind": kind, "grants": [list(g) for g in grants],
                  "exp": self._clock() + min(ttl, self.max_ttl), "att": attested, "jti": os.urandom(8).hex()}
        body = base64.urlsafe_b64encode(json.dumps(claims, sort_keys=True).encode()).decode()
        return f"{body}.{self.keys.mac(body.encode())}"

    def authenticate(self, credential: str) -> Principal:
        if not self.keys.available:
            raise TrustUnavailableError("identity service unavailable; failing closed")
        if not isinstance(credential, str) or credential.count(".") != 1 or len(credential) > 8192:
            raise AuthenticationError("malformed credential")
        body, tag = credential.split(".")
        if not self.keys.verify_mac(body.encode(), tag):
            raise AuthenticationError("credential signature invalid")
        try:
            claims = json.loads(base64.urlsafe_b64decode(body.encode()))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthenticationError("credential body invalid") from exc
        if claims.get("exp", 0) <= self._clock():
            raise AuthenticationError("credential expired")
        if claims.get("jti") in self.revoked:
            raise AuthenticationError("credential revoked")
        return Principal(subject=claims["sub"], kind=claims["kind"],
                         grants=tuple(tuple(g) for g in claims["grants"]), attested=bool(claims.get("att")))


def authorize(principal: Principal, capability: str, tenant: str, environment: str) -> None:
    if capability not in CAPABILITIES:
        raise AuthorizationError(f"unknown capability {capability}")
    if not principal.allows(capability, tenant, environment):
        raise AuthorizationError(f"{principal.subject} lacks {capability} on {tenant}/{environment}")


@dataclass
class ArtifactPolicy:
    """Artifact admission policy: digest pin + trusted signer + approved versions."""

    keys: KeyProvider
    trusted_signers: set[str] = field(default_factory=set)
    approved_digests: dict[str, set[str]] = field(default_factory=dict)   # name -> digests
    require_provenance: bool = True
    revoked_digests: set[str] = field(default_factory=set)

    def sign(self, name: str, digest: str, signer: str) -> str:
        return self.keys.mac(f"{name}\n{digest}\n{signer}".encode())

    def verify(self, artifact: Mapping[str, Any]) -> None:
        name, digest = artifact.get("name"), artifact.get("digest")
        if not (isinstance(digest, str) and digest.startswith("sha256:") and len(digest) == 71):
            raise ArtifactVerificationError(f"artifact {name} lacks a sha256 digest pin")
        if digest in self.revoked_digests:
            raise ArtifactVerificationError(f"artifact {name} digest is revoked")
        if name not in self.approved_digests or digest not in self.approved_digests[name]:
            raise ArtifactVerificationError(f"artifact {name}@{digest} is not an approved version")
        signer = artifact.get("signer")
        if signer not in self.trusted_signers:
            raise ArtifactVerificationError(f"artifact {name} signer {signer!r} is not trusted")
        if not self.keys.verify_mac(f"{name}\n{digest}\n{signer}".encode(), artifact.get("signature", "")):
            raise ArtifactVerificationError(f"artifact {name} signature invalid")
        if self.require_provenance:
            prov = artifact.get("provenance")
            if not isinstance(prov, Mapping) or not prov.get("builder") or not prov.get("source"):
                raise ArtifactVerificationError(f"artifact {name} lacks builder/source provenance")


class StaticPolicyAdapter:
    """External policy adapter (GAP-13 seam) with fail-closed timeout behaviour."""

    def __init__(self, evaluate: Callable[[dict[str, Any]], tuple[bool, str]]) -> None:
        self._evaluate = evaluate
        self.available = True
        self._lock = threading.Lock()

    def __call__(self, key, spec, deps, actor) -> tuple[bool, str]:
        if not self.available:
            return False, "policy engine unavailable; failing closed"
        try:
            return self._evaluate({"node": list(key), "spec": spec, "after": [list(d) for d in deps], "actor": actor})
        except Exception as exc:  # noqa: BLE001
            return False, f"policy engine error; failing closed ({type(exc).__name__})"
