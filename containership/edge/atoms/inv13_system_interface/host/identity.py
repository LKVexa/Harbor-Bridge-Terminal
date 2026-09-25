"""MC-006 -- actor identity and attestation gate.

Actors (runtime node, control plane, operator) present HMAC-SHA256 signed
tokens ``{sub, role, workload?, node?, exp, nonce}``; the verifier checks key
id, signature (constant time), expiry against an injected clock, audience,
replay (nonce cache) and workload binding.  Attestation is a pluggable
``AttestationVerifier``; when a policy *requires* attestation and none is
available the gate fails closed (ATTESTATION_FAILED), never open.

HMAC with a shared key is the reference mechanism; production swaps
``KeyRing`` for the fleet PKI / SPIFFE / hardware-rooted verifier behind the
same interface.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from typing import Any, Callable, Protocol

from .errors import ErrorCode, Inv13Error


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    """Strict, canonical base64url: rejects non-alphabet chars and non-zero padding bits
    (otherwise several token strings decode to one signature -- token malleability)."""
    raw = base64.urlsafe_b64decode((s + "=" * (-len(s) % 4)).encode("ascii"))
    if _b64(raw) != s:
        raise ValueError("non-canonical base64url")
    return raw


class KeyRing:
    def __init__(self, keys: dict[str, bytes]) -> None:
        for kid, k in keys.items():
            if len(k) < 32:
                raise ValueError(f"key {kid} shorter than 256 bits")
        self._keys = dict(keys)

    def sign(self, kid: str, claims: dict[str, Any]) -> str:
        payload = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        mac = hmac.new(self._keys[kid], f"{kid}.{payload}".encode(), hashlib.sha256).digest()
        return f"{kid}.{payload}.{_b64(mac)}"

    def key(self, kid: str) -> bytes | None:
        return self._keys.get(kid)


class AttestationVerifier(Protocol):
    def verify(self, node: str, evidence: bytes) -> bool: ...


class IdentityGate:
    def __init__(self, keyring: KeyRing, *, audience: str, clock: Callable[[], float],
                 attestation: AttestationVerifier | None = None, require_attestation: bool = False,
                 max_ttl: float = 3600.0) -> None:
        self.keyring, self.audience, self.clock = keyring, audience, clock
        self.attestation, self.require_attestation, self.max_ttl = attestation, require_attestation, max_ttl
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def verify(self, token: Any, *, role: str, workload: str | None = None,
               attestation_evidence: bytes | None = None) -> dict[str, Any]:
        if not isinstance(token, str) or token.count(".") != 2 or len(token) > 8192:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "malformed")
        kid, payload, sig = token.split(".")
        key = self.keyring.key(kid)
        if key is None:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "unknown kid")
        want = hmac.new(key, f"{kid}.{payload}".encode(), hashlib.sha256).digest()
        try:
            got = _unb64(sig)
            claims = json.loads(_unb64(payload))
        except Exception:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "decode") from None
        if not hmac.compare_digest(want, got):
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "signature")
        now = self.clock()
        exp = claims.get("exp")
        if not isinstance(exp, (int, float)) or exp <= now or exp - now > self.max_ttl:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "expiry")
        if claims.get("aud") != self.audience or claims.get("role") != role:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "audience/role")
        if workload is not None and claims.get("workload") != workload:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "workload binding")
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or len(nonce) < 16:
            raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "nonce")
        with self._lock:
            self._seen = {n: e for n, e in self._seen.items() if e > now}
            if nonce in self._seen:
                raise Inv13Error(ErrorCode.IDENTITY_REQUIRED, "replay")
            self._seen[nonce] = exp
        if self.require_attestation:
            if self.attestation is None or attestation_evidence is None:
                raise Inv13Error(ErrorCode.ATTESTATION_FAILED, "unavailable")
            try:
                ok = self.attestation.verify(claims.get("node", ""), attestation_evidence)
            except Exception:
                ok = False
            if not ok:
                raise Inv13Error(ErrorCode.ATTESTATION_FAILED, "rejected")
        return claims
