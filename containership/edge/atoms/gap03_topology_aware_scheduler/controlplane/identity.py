"""MC-012 - Identity, attestation and topology-provenance verification.

Trust model (GAP03-ID/1):
* identities are ``spiffe://<trust_domain>/<kind>/<name>`` strings;
* credentials are canonical-JSON claim sets signed with Ed25519 by an issuer
  listed in a :class:`TrustStore`; the only accepted algorithm is ``Ed25519``
  (anything else - ``none``, ``HS256`` - is a downgrade and is rejected);
* verification checks alg, issuer, kid validity window, revocation, signature,
  audience, nbf/exp with bounded skew, and single-use nonce (bounded cache);
* every failure raises ``SchedulerError('UNAUTHENTICATED'|'REPLAY_DETECTED')``
  and emits an audit event through the optional sink.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import base64
import os
import re
import threading
import time

from . import canonical, ed25519
from .errors import SchedulerError

ALGORITHMS = frozenset({"Ed25519"})
MAX_SKEW_S = 30
MAX_TOKEN_LIFETIME_S = 3600
IDENTITY_RE = re.compile(r"^spiffe://[a-z0-9.\-]{1,63}/(workload|service|node|operator|issuer)/[A-Za-z0-9._\-]{1,63}$")
IDENTITY_KINDS = {
    "operator": {"may_assert": ["topology.mutate", "entitlement.write", "control.write", "config.write"]},
    "service": {"may_assert": ["placement.commit", "explain.read", "topology.read"]},
    "workload": {"may_assert": ["placement.request"]},
    "node": {"may_assert": ["capability.report", "latency.report"]},
    "issuer": {"may_assert": ["credential.issue", "artifact.sign"]},
}


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass
class IssuerKey:
    kid: str
    public: bytes
    not_before: float
    not_after: float
    revoked: bool = False


@dataclass
class SigningKey:
    """A private key held by reference.  ``secret_ref`` names where it lives (env:/file:/kms:)."""
    kid: str
    issuer: str
    secret: bytes = field(repr=False)
    secret_ref: str = "ephemeral:test"

    @classmethod
    def generate(cls, kid: str, issuer: str) -> "SigningKey":
        return cls(kid, issuer, os.urandom(32))

    @classmethod
    def from_ref(cls, kid: str, issuer: str, ref: str) -> "SigningKey":
        if ref.startswith("env:"):
            raw = os.environ.get(ref[4:])
            if not raw:
                raise SchedulerError("DEPENDENCY_UNAVAILABLE", "signing key reference unresolved")
            return cls(kid, issuer, unb64(raw), ref)
        if ref.startswith("file:"):
            with open(ref[5:], "rb") as fh:
                return cls(kid, issuer, unb64(fh.read().decode().strip()), ref)
        raise SchedulerError("DEPENDENCY_UNAVAILABLE", "unsupported key reference scheme (kms: requires an HSM adapter)")

    @property
    def public(self) -> bytes:
        return ed25519.public_key(self.secret)

    def sign(self, msg: bytes) -> bytes:
        return ed25519.sign(self.secret, msg)


class ReplayCache:
    """Bounded single-use nonce cache; entries expire after ``ttl`` seconds."""

    def __init__(self, max_entries: int = 100_000, ttl: float = MAX_TOKEN_LIFETIME_S + MAX_SKEW_S):
        self._seen: "OrderedDict[str, float]" = OrderedDict()
        self._lock = threading.Lock()
        self.max_entries, self.ttl = max_entries, ttl

    def check_and_add(self, nonce: str, now: float) -> bool:
        with self._lock:
            while self._seen and next(iter(self._seen.values())) < now - self.ttl:
                self._seen.popitem(last=False)
            if nonce in self._seen:
                return False
            if len(self._seen) >= self.max_entries:
                # fail closed: a full cache cannot prove freshness
                raise SchedulerError("OVERLOADED", "replay cache full")
            self._seen[nonce] = now
            return True


class TrustStore:
    def __init__(self, *, clock=time.time, audit=None, metrics=None):
        self.metrics = metrics
        self.issuers: dict[str, dict[str, IssuerKey]] = {}
        self.clock = clock
        self.audit = audit
        self.replay = ReplayCache()
        self.generation = 0
        self._lock = threading.RLock()

    def _event(self, action: str, result: str, **detail):
        if self.audit is not None:
            self.audit.append(actor=detail.pop("actor", "system"), action=action, target=detail.pop("target", "trust"),
                              result=result, detail=detail)

    def add_key(self, issuer: str, kid: str, public: bytes, *, not_before: float | None = None,
                not_after: float | None = None, actor: str = "system"):
        now = self.clock()
        with self._lock:
            self.issuers.setdefault(issuer, {})[kid] = IssuerKey(kid, public, now - 1 if not_before is None else not_before,
                                                                 now + 86400 * 90 if not_after is None else not_after)
            self.generation += 1
        self._event("trust.key_added", "ok", actor=actor, target=f"{issuer}#{kid}")

    def revoke(self, issuer: str, kid: str, *, actor: str = "system"):
        with self._lock:
            self.issuers[issuer][kid].revoked = True
            self.generation += 1
        self._event("trust.key_revoked", "ok", actor=actor, target=f"{issuer}#{kid}")

    def remove_issuer(self, issuer: str, *, actor: str = "system"):
        with self._lock:
            self.issuers.pop(issuer, None)
            self.generation += 1
        self._event("trust.root_removed", "ok", actor=actor, target=issuer)

    def _key(self, issuer: str, kid: str, now: float) -> IssuerKey:
        keys = self.issuers.get(issuer)
        if not keys:
            raise SchedulerError("UNAUTHENTICATED", "unknown issuer")
        key = keys.get(kid)
        if key is None:
            raise SchedulerError("UNAUTHENTICATED", "unknown key id")
        if key.revoked:
            raise SchedulerError("UNAUTHENTICATED", "key revoked")
        if not (key.not_before - MAX_SKEW_S <= now <= key.not_after + MAX_SKEW_S):
            raise SchedulerError("UNAUTHENTICATED", "key outside validity window")
        return key

    # ---- tokens -----------------------------------------------------------------
    def verify_token(self, token: str, *, audience: str, consume_nonce: bool = True) -> dict:
        now = self.clock()
        try:
            body_b64, sig_b64 = token.split(".")
            header_claims = canonical.loads(unb64(body_b64), max_bytes=8192)
            sig = unb64(sig_b64)
        except Exception:
            self._event("auth.verify_failed", "denied", reason="malformed")
            raise SchedulerError("UNAUTHENTICATED", "malformed credential") from None
        try:
            if header_claims.get("alg") not in ALGORITHMS:
                self._event("auth.downgrade_attempt", "denied", alg=str(header_claims.get("alg"))[:16])
                raise SchedulerError("UNAUTHENTICATED", "algorithm not allowed")
            key = self._key(header_claims.get("iss", ""), header_claims.get("kid", ""), now)
            if not ed25519.verify(key.public, unb64(body_b64), sig):
                raise SchedulerError("UNAUTHENTICATED", "bad signature")
            if header_claims.get("aud") != audience:
                raise SchedulerError("UNAUTHENTICATED", "wrong audience")
            if not IDENTITY_RE.match(str(header_claims.get("sub", ""))):
                raise SchedulerError("UNAUTHENTICATED", "malformed subject identity")
            nbf, exp = header_claims.get("nbf", 0), header_claims.get("exp", 0)
            if not isinstance(nbf, int) or not isinstance(exp, int) or exp - nbf > MAX_TOKEN_LIFETIME_S:
                raise SchedulerError("UNAUTHENTICATED", "invalid validity window")
            if now + MAX_SKEW_S < nbf:
                raise SchedulerError("UNAUTHENTICATED", "not yet valid")
            if now - MAX_SKEW_S > exp:
                raise SchedulerError("UNAUTHENTICATED", "expired")
            if consume_nonce and not self.replay.check_and_add(str(header_claims.get("nonce", "")), now):
                self._event("auth.replay", "denied", sub=header_claims.get("sub"))
                raise SchedulerError("REPLAY_DETECTED", "nonce already used")
        except SchedulerError as exc:
            if exc.code == "UNAUTHENTICATED":
                self._event("auth.verify_failed", "denied", reason=exc.reason)
            if self.metrics:
                self.metrics.inc("gap03_trust_verifications_total", result=exc.code)
            raise
        if self.metrics:
            self.metrics.inc("gap03_trust_verifications_total", result="ok")
        return header_claims


def issue_token(key: SigningKey, *, subject: str, audience: str, roles: list[str], clock=time.time,
                lifetime: int = 300, nonce: str | None = None, extra: dict | None = None, alg: str = "Ed25519") -> str:
    now = int(clock())
    claims = {"alg": alg, "iss": key.issuer, "kid": key.kid, "sub": subject, "aud": audience, "roles": sorted(roles),
              "iat": now, "nbf": now, "exp": now + lifetime, "nonce": nonce or b64(os.urandom(16))}
    claims.update(extra or {})
    body = canonical.dumps(claims)
    return b64(body) + "." + b64(key.sign(body))


def trust_domain(identity: str) -> str:
    return identity.split("/")[2]


def identity_kind(identity: str) -> str:
    return identity.split("/")[3]


# ---- artifact provenance ---------------------------------------------------------------
def sign_artifact(key: SigningKey, kind: str, obj, *, clock=time.time, version: str = "1") -> dict:
    stmt = {"kind": kind, "version": version, "digest": canonical.digest(obj), "issuer": key.issuer, "kid": key.kid,
            "signed_at": int(clock()), "alg": "Ed25519"}
    return {"statement": stmt, "signature": b64(key.sign(canonical.dumps(stmt)))}


def verify_artifact(store: TrustStore, envelope: dict, obj, *, kind: str) -> dict:
    stmt = envelope.get("statement", {})
    if stmt.get("alg") not in ALGORITHMS:
        store._event("provenance.downgrade_attempt", "denied", kind=kind)
        raise SchedulerError("UNAUTHENTICATED", "algorithm not allowed")
    if stmt.get("kind") != kind:
        raise SchedulerError("UNAUTHENTICATED", "artifact kind mismatch")
    key = store._key(stmt.get("issuer", ""), stmt.get("kid", ""), store.clock())
    if not ed25519.verify(key.public, canonical.dumps(stmt), unb64(envelope.get("signature", ""))):
        store._event("provenance.verify_failed", "denied", kind=kind)
        raise SchedulerError("UNAUTHENTICATED", "artifact signature invalid")
    if stmt["digest"] != canonical.digest(obj):
        store._event("provenance.verify_failed", "denied", kind=kind, reason="digest")
        raise SchedulerError("INTEGRITY_FAILURE", "artifact digest mismatch")
    return stmt


# ---- attestation ------------------------------------------------------------------------
ATTESTATION_REQUIREMENTS = {
    "confidential": {"tee": True, "secure_boot": True, "measurement_allowlisted": True},
    "accelerated": {"secure_boot": True},
    "general": {},
}


def verify_attestation(store: TrustStore, node_class: str, report: dict | None, *, measurement_allowlist: set[str]) -> dict:
    """Fail closed: a security-sensitive class without verifiable claims is refused."""
    required = ATTESTATION_REQUIREMENTS.get(node_class)
    if required is None:
        raise SchedulerError("INVALID_ARGUMENT", "unknown node class")
    if not required:
        return {"node_class": node_class, "verified": True, "claims": {}}
    if not report:
        store._event("attestation.missing", "denied", node_class=node_class)
        raise SchedulerError("UNAUTHENTICATED", "attestation required")
    claims = report.get("claims", {})
    verify_artifact(store, report.get("envelope", {}), claims, kind="attestation")
    got = {"tee": bool(claims.get("tee")), "secure_boot": bool(claims.get("secure_boot")),
           "measurement_allowlisted": claims.get("measurement") in measurement_allowlist}
    missing = [k for k, v in required.items() if got.get(k) != v]
    if missing:
        store._event("attestation.claims_failed", "denied", node_class=node_class, missing=missing)
        raise SchedulerError("UNAUTHENTICATED", f"attestation claims unmet: {missing}")
    return {"node_class": node_class, "verified": True, "claims": got}
