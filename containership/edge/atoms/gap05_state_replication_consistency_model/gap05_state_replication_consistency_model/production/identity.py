"""MC01 - Authenticated replica identity.

Trust mechanism (documented choice, MC01-003): an Ed25519 workload-certificate scheme
modelled on SPIFFE X.509-SVIDs.  A trust domain's certificate authority signs
``WorkloadCredential`` records binding a canonical workload ID
(``spiffe://<trust-domain>/replica/<name>``) to a public key for a bounded validity
window.  A peer authenticates by signing a single-use server nonce together with the
transport channel-binding value, so a captured handshake cannot be replayed on another
connection (MC01-010).  Real mTLS/SPIRE deployment is an integration step outside this
package; this module is the verification core such a deployment must call.

Time is injected (``now``) so expiry is testable; identity decisions never feed causal
ordering.
"""
from __future__ import annotations

import base64
import hashlib
import os
import threading
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .errors import AuthenticationError, ConfigError
from .schemas import canonical_bytes

SPIFFE_PREFIX = "spiffe://"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def pub_bytes(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def fingerprint(key: Ed25519PublicKey) -> str:
    return hashlib.sha256(pub_bytes(key)).hexdigest()[:32]


def workload_id(trust_domain: str, replica: str) -> str:
    """Canonical identity: stable across restarts, host renames, IP changes (MC01-001)."""
    if not trust_domain or "/" in trust_domain or not replica or "/" in replica or "*" in replica:
        raise ConfigError("trust domain and replica must be non-empty path segments without wildcards")
    return f"{SPIFFE_PREFIX}{trust_domain}/replica/{replica}"


@dataclass(frozen=True)
class WorkloadCredential:
    workload_id: str
    public_key: bytes
    serial: str
    not_before: int
    not_after: int
    issuer: str
    signature: str

    def body(self) -> dict:
        return {"workload_id": self.workload_id, "public_key": b64(self.public_key), "serial": self.serial,
                "not_before": self.not_before, "not_after": self.not_after, "issuer": self.issuer}


class CertificateAuthority:
    """Test/bootstrap CA for one trust domain.  Production would delegate to SPIRE/PKI."""

    def __init__(self, trust_domain: str, *, key: Ed25519PrivateKey | None = None):
        self.trust_domain = trust_domain
        self._key = key or Ed25519PrivateKey.generate()
        self.ca_id = fingerprint(self._key.public_key())

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self._key.public_key()

    def issue(self, replica: str, public_key: Ed25519PublicKey, *, now: int, ttl: int) -> WorkloadCredential:
        if ttl <= 0:
            raise ConfigError("ttl must be positive")
        wid = workload_id(self.trust_domain, replica)
        body = {"workload_id": wid, "public_key": b64(pub_bytes(public_key)), "serial": os.urandom(8).hex(),
                "not_before": now, "not_after": now + ttl, "issuer": self.ca_id}
        sig = self._key.sign(canonical_bytes(body))
        return WorkloadCredential(wid, pub_bytes(public_key), body["serial"], now, now + ttl, self.ca_id, b64(sig))


@dataclass
class AuthenticatedPeer:
    replica: str
    workload_id: str
    key_fingerprint: str
    epoch: int
    session_id: str
    channel_binding: str


@dataclass
class TrustBundle:
    """Pinned CA keys for the trust domain.  Rotation = add new, migrate, remove old."""

    trust_domain: str
    authorities: dict[str, Ed25519PublicKey] = field(default_factory=dict)

    def add(self, ca_public: Ed25519PublicKey) -> str:
        cid = fingerprint(ca_public)
        self.authorities[cid] = ca_public
        return cid

    def remove(self, ca_id: str) -> None:
        if len(self.authorities) <= 1 and ca_id in self.authorities:
            raise ConfigError("refusing to remove the last trust anchor (would fail all sessions)")
        self.authorities.pop(ca_id, None)


class IdentityVerifier:
    """Verifies credentials and handshakes and maps identities to replicas for an epoch."""

    def __init__(self, bundle: TrustBundle, *, grace_seconds: int = 0):
        self.bundle = bundle
        self.grace_seconds = grace_seconds
        self._revoked: set[str] = set()
        self._nonces: dict[str, str] = {}
        self._lock = threading.Lock()
        self.max_outstanding_nonces = 10_000

    # -- revocation (MC01-006) --------------------------------------------------
    def revoke(self, serial: str) -> None:
        self._revoked.add(serial)

    def verify_credential(self, cred: WorkloadCredential, *, now: int) -> Ed25519PublicKey:
        ca = self.bundle.authorities.get(cred.issuer)
        if ca is None:
            raise AuthenticationError("credential issuer is not a pinned trust anchor", code="SEC_UNTRUSTED_ISSUER")
        try:
            ca.verify(unb64(cred.signature), canonical_bytes(cred.body()))
        except InvalidSignature as exc:
            raise AuthenticationError("credential signature invalid", code="SEC_BAD_CREDENTIAL") from exc
        if not cred.workload_id.startswith(f"{SPIFFE_PREFIX}{self.bundle.trust_domain}/replica/"):
            raise AuthenticationError("credential outside trust domain", code="SEC_WRONG_TRUST_DOMAIN")
        if "*" in cred.workload_id:
            raise AuthenticationError("wildcard identities are not accepted", code="SEC_WILDCARD")
        if cred.serial in self._revoked:
            raise AuthenticationError("credential revoked", code="SEC_REVOKED")
        if now < cred.not_before or now > cred.not_after + self.grace_seconds:
            raise AuthenticationError("credential outside validity window", code="SEC_EXPIRED")
        return Ed25519PublicKey.from_public_bytes(cred.public_key)

    # -- handshake (MC01-002/004/005/010) --------------------------------------
    def challenge(self, channel_binding: str) -> str:
        if not channel_binding:
            raise AuthenticationError("channel binding required", code="SEC_NO_CHANNEL_BINDING")
        with self._lock:
            if len(self._nonces) >= self.max_outstanding_nonces:
                raise AuthenticationError("too many outstanding challenges", code="CAP_HANDSHAKE")
            nonce = os.urandom(16).hex()
            self._nonces[nonce] = channel_binding
            return nonce

    @staticmethod
    def handshake_payload(nonce: str, channel_binding: str, wid: str) -> bytes:
        return canonical_bytes({"nonce": nonce, "cb": channel_binding, "wid": wid, "ctx": "GAP05-HANDSHAKE/1"})

    def authenticate(self, cred: WorkloadCredential, nonce: str, signature: str, *, channel_binding: str,
                     now: int, membership) -> AuthenticatedPeer:
        with self._lock:
            bound = self._nonces.pop(nonce, None)
        if bound is None:
            raise AuthenticationError("unknown or reused nonce", code="SEC_REPLAY")
        if bound != channel_binding:
            raise AuthenticationError("handshake bound to a different channel", code="SEC_CHANNEL_MISMATCH")
        key = self.verify_credential(cred, now=now)
        try:
            key.verify(unb64(signature), self.handshake_payload(nonce, channel_binding, cred.workload_id))
        except InvalidSignature as exc:
            raise AuthenticationError("proof-of-possession failed", code="SEC_BAD_POP") from exc
        replica = membership.replica_for_identity(cred.workload_id, fingerprint(key))
        return AuthenticatedPeer(replica=replica, workload_id=cred.workload_id, key_fingerprint=fingerprint(key),
                                 epoch=membership.epoch, session_id=os.urandom(8).hex(),
                                 channel_binding=channel_binding)


@dataclass
class ReplicaKeys:
    """A replica's own signing key plus its CA-issued credential."""

    replica: str
    private_key: Ed25519PrivateKey
    credential: WorkloadCredential

    @classmethod
    def provision(cls, ca: CertificateAuthority, replica: str, *, now: int, ttl: int = 86_400) -> "ReplicaKeys":
        key = Ed25519PrivateKey.generate()
        return cls(replica, key, ca.issue(replica, key.public_key(), now=now, ttl=ttl))

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.private_key.public_key())

    def answer(self, nonce: str, channel_binding: str) -> str:
        return b64(self.private_key.sign(
            IdentityVerifier.handshake_payload(nonce, channel_binding, self.credential.workload_id)))
