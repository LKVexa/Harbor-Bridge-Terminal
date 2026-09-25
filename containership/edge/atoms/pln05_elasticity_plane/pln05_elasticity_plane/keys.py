"""Key ring and transport policy for PLN-05 (stdlib only).

* :class:`KeyRing` holds HMAC-SHA256 keys with ``kid``, validity window and
  revocation, supporting overlapping rotation (sign with the newest active key,
  verify with any key still in its window).  It backs credential verification
  (``iam``), audit anchoring (``audit``) and state integrity (``state``).
* :class:`TransportPolicy` is the decision function a transport adapter must
  call before accepting a peer: minimum protocol version (downgrade refusal),
  approved cipher suites, workload-identity match and certificate expiry and
  revocation.  This package ships no network listener; the policy is enforced at
  the adapter seam and tested here.

Confidentiality at rest is delegated (see ``security/crypto-policy.md``): the
package stores no secrets in state, and state/config/audit integrity is
protected by HMAC with keys from this ring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import secrets

from .errors import PlaneError


@dataclass
class Key:
    kid: str
    secret: bytes = field(repr=False)
    not_before: float
    not_after: float
    revoked: bool = False

    def active(self, now: float) -> bool:
        return (not self.revoked) and self.not_before <= now < self.not_after


class KeyRing:
    """Rotating HMAC key ring.  Secrets never appear in ``repr`` or status."""

    MAX_KEYS = 16

    def __init__(self) -> None:
        self._keys: dict[str, Key] = {}
        self.available = True  # False simulates KMS outage: no new keys, cache still bounded

    def add(self, kid: str, secret: bytes, not_before: float, not_after: float) -> None:
        if not isinstance(secret, (bytes, bytearray)) or len(secret) < 32:
            raise PlaneError("E_CONFIG_INVALID", "key material must be >= 32 bytes")
        if not_after <= not_before:
            raise PlaneError("E_CONFIG_INVALID", "key window is empty")
        if len(self._keys) >= self.MAX_KEYS and kid not in self._keys:
            raise PlaneError("E_OVERLOADED", "key ring full")
        self._keys[kid] = Key(kid, bytes(secret), float(not_before), float(not_after))

    @classmethod
    def ephemeral(cls, now: float, lifetime: float = 86400.0, kid: str = "k1",
                  backdate: float = 3600.0) -> "KeyRing":
        ring = cls()
        ring.add(kid, secrets.token_bytes(32), now - backdate, now + lifetime)
        return ring

    def revoke(self, kid: str) -> None:
        if kid in self._keys:
            self._keys[kid].revoked = True

    def signing_key(self, now: float) -> Key:
        live = [k for k in self._keys.values() if k.active(now)]
        if not live:
            raise PlaneError("E_SECURITY_DEPENDENCY", "no active signing key")
        return max(live, key=lambda k: (k.not_before, k.kid))

    def sign(self, data: bytes, now: float) -> tuple[str, str]:
        key = self.signing_key(now)
        return key.kid, hmac.new(key.secret, data, hashlib.sha256).hexdigest()

    def verify(self, kid: str, data: bytes, mac: str, now: float) -> None:
        key = self._keys.get(kid)
        if key is None:
            raise PlaneError("E_AUTHN_FAILED", "unknown key id")
        if key.revoked:
            raise PlaneError("E_AUTHN_REVOKED", "key revoked")
        if not key.active(now):
            raise PlaneError("E_AUTHN_EXPIRED", "key outside validity window")
        want = hmac.new(key.secret, data, hashlib.sha256).hexdigest()
        if not isinstance(mac, str) or not hmac.compare_digest(want, mac):
            raise PlaneError("E_AUTHN_FAILED", "signature mismatch")

    def status(self, now: float) -> list[dict]:
        return [{"kid": k.kid, "active": k.active(now), "revoked": k.revoked,
                 "not_after": k.not_after} for k in sorted(self._keys.values(), key=lambda k: k.kid)]


PROTOCOL_ORDER = {"TLSv1.0": 10, "TLSv1.1": 11, "TLSv1.2": 12, "TLSv1.3": 13}
APPROVED_CIPHERS = frozenset({
    "TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES128-GCM-SHA256", "ECDHE-RSA-AES256-GCM-SHA384",
})


@dataclass(frozen=True)
class TransportPolicy:
    minimum: str = "TLSv1.2"
    require_mutual: bool = True

    def check_peer(self, *, protocol: str, cipher: str, peer_identity: str | None,
                   expected_identity: str, cert_not_after: float, revoked: bool,
                   now: float, mutual: bool) -> None:
        if PROTOCOL_ORDER.get(protocol, 0) < PROTOCOL_ORDER[self.minimum]:
            raise PlaneError("E_AUTHN_FAILED", "transport protocol below policy minimum",
                             {"minimum": self.minimum})
        if cipher not in APPROVED_CIPHERS:
            raise PlaneError("E_AUTHN_FAILED", "cipher not approved")
        if self.require_mutual and not mutual:
            raise PlaneError("E_AUTHN_FAILED", "mutual authentication required")
        if peer_identity != expected_identity:
            raise PlaneError("E_AUTHN_FAILED", "peer workload identity mismatch")
        if revoked:
            raise PlaneError("E_AUTHN_REVOKED", "peer certificate revoked")
        if now >= cert_not_after:
            raise PlaneError("E_AUTHN_EXPIRED", "peer certificate expired")
