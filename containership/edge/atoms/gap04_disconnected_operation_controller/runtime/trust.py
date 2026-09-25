"""Trust store, signed leases, signed policy bundles, revocation epochs.

Covers GAP04-C01 (signed lease envelope), C05 (policy integrity/provenance),
C06 (revocation epoch/watermark). All verification is fail-closed: any
uncertainty raises a ``Gap04Error`` with a stable code and nothing is accepted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from . import canonical, crypto
from .errors import Gap04Error

LEASE_VERSION = "PK_SIGNED_LEASE/1"
POLICY_VERSION = "PK_POLICY_BUNDLE/1"
TRUST_VERSION = "PK_TRUST_BUNDLE/1"
SUPPORTED_LEASE_VERSIONS = frozenset({LEASE_VERSION})
MAX_LEASE_LIFETIME_S = 7 * 24 * 3600
MAX_CLOCK_SKEW_S = 120
NONCE_RE = re.compile(r"^[0-9a-f]{32,128}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
CAPABILITIES = frozenset({"restart", "rebalance", "admit-known", "admit-new", "scale"})
SCOPE_KEYS = ("site", "tenant", "cluster", "node_class", "environment")
LEASE_FIELDS = frozenset({"version", "issuer", "trust_domain", "scope", "lease_id", "issued_at", "not_before",
                          "expires_at", "policy", "capabilities", "authority_epoch", "nonce", "key_id", "alg", "sig"})


def _err(code: str, msg: str, **details: Any) -> Gap04Error:
    return Gap04Error(msg, code=code, details=details)


@dataclass
class TrustKey:
    key_id: str
    issuer: str
    alg: str
    public_key: str
    not_before: int
    not_after: int
    purposes: frozenset[str]
    revoked: bool = False


@dataclass
class TrustStore:
    """Explicit trust anchors. Loaded from a PK_TRUST_BUNDLE/1 document which is
    itself distributed through the control plane; bundle_version must never go
    backwards (stale-bundle recovery is by replacing with a newer bundle)."""

    trust_domain: str
    bundle_version: int
    keys: dict[str, TrustKey] = field(default_factory=dict)

    @classmethod
    def from_doc(cls, doc: Mapping[str, Any], *, min_version: int = 0) -> "TrustStore":
        if not isinstance(doc, Mapping) or doc.get("version") != TRUST_VERSION:
            raise _err("GAP04-E0208", "trust bundle missing or wrong version")
        bv = doc.get("bundle_version")
        if not isinstance(bv, int) or isinstance(bv, bool) or bv < min_version:
            raise _err("GAP04-E0208", "trust bundle version stale", bundle_version=bv, min_version=min_version)
        ts = cls(trust_domain=str(doc["trust_domain"]), bundle_version=bv)
        for k in doc.get("keys", []):
            if k.get("alg") not in crypto.ALLOWED_SIG_ALGS:
                raise _err("GAP04-E0203", "trust bundle contains a non-allow-listed algorithm", key_id=k.get("key_id"))
            ts.keys[k["key_id"]] = TrustKey(k["key_id"], k["issuer"], k["alg"], k["public_key"], int(k["not_before"]),
                                            int(k["not_after"]), frozenset(k.get("purposes", ["lease"])), bool(k.get("revoked", False)))
        return ts

    def to_doc(self) -> dict:
        return {"version": TRUST_VERSION, "trust_domain": self.trust_domain, "bundle_version": self.bundle_version,
                "keys": [{"key_id": k.key_id, "issuer": k.issuer, "alg": k.alg, "public_key": k.public_key,
                          "not_before": k.not_before, "not_after": k.not_after, "purposes": sorted(k.purposes),
                          "revoked": k.revoked} for k in sorted(self.keys.values(), key=lambda k: k.key_id)]}

    def resolve(self, key_id: str, issuer: str, alg: str, purpose: str, at: int) -> TrustKey:
        if alg not in crypto.ALLOWED_SIG_ALGS:
            raise _err("GAP04-E0203", "algorithm not allowed", alg=alg)
        k = self.keys.get(key_id)
        if k is None or k.issuer != issuer:
            raise _err("GAP04-E0202", "unknown issuer/key", key_id=key_id, issuer=issuer)
        if k.revoked:
            raise _err("GAP04-E0202", "key revoked", key_id=key_id)
        if purpose not in k.purposes:
            raise _err("GAP04-E0202", "key not authorized for purpose", key_id=key_id, purpose=purpose)
        if k.alg != alg:
            raise _err("GAP04-E0203", "algorithm substitution", key_id=key_id)
        if not (k.not_before <= at <= k.not_after):
            raise _err("GAP04-E0202", "key outside validity window", key_id=key_id)
        return k


@dataclass(frozen=True)
class VerifiedLease:
    lease_id: str
    fingerprint: str
    issuer: str
    key_id: str
    scope: Mapping[str, str]
    issued_at: int
    not_before: int
    expires_at: int
    policy_version: int
    policy_digest: str
    capabilities: frozenset[str]
    authority_epoch: int
    nonce: str

    def audit_view(self) -> dict:
        """Audit-safe projection: no key material, capabilities by digest only (C01-015)."""
        return {"lease_id": self.lease_id, "fingerprint": self.fingerprint, "issuer": self.issuer,
                "key_id": self.key_id, "authority_epoch": self.authority_epoch, "policy_digest": self.policy_digest,
                "policy_version": self.policy_version, "expires_at": self.expires_at,
                "capabilities_digest": canonical.digest(sorted(self.capabilities)), "result": "verified"}


def lease_payload(env: Mapping[str, Any]) -> dict:
    return {k: v for k, v in env.items() if k != "sig"}


def sign_lease(payload: Mapping[str, Any], seed: bytes) -> dict:
    """Issuer-side helper (control plane / tests). Produces a canonical envelope."""
    body = dict(payload)
    body["capabilities"] = sorted(body["capabilities"])
    body["sig"] = crypto.sign(seed, canonical.dumps(body))
    return body


def _int(env, name):
    v = env.get(name)
    if not isinstance(v, int) or isinstance(v, bool) or v < 0:
        raise _err("GAP04-E0200", f"{name} must be a non-negative integer")
    return v


def verify_lease(raw: bytes | str | Mapping[str, Any], *, trust: TrustStore | None, expected_scope: Mapping[str, str],
                 now: int, min_authority_epoch: int, expected_policy_digest: str | None,
                 revoked_lease_ids: frozenset[str] = frozenset()) -> VerifiedLease:
    """Verify a signed lease envelope. Fails closed at every step (C01-003, C01-012)."""
    if trust is None:
        raise _err("GAP04-E0208", "trust store unavailable")
    crypto.require_backend()
    try:
        env = canonical.loads(raw) if isinstance(raw, (bytes, str)) else dict(raw)
        canonical.dumps(env)
    except canonical.CanonicalError as e:
        raise _err("GAP04-E0200", f"lease envelope non-canonical: {e}") from None
    if not isinstance(env, dict):
        raise _err("GAP04-E0200", "lease envelope must be an object")
    if env.get("version") not in SUPPORTED_LEASE_VERSIONS:
        raise _err("GAP04-E0209", "unsupported lease envelope version", version=env.get("version"))
    if set(env) != LEASE_FIELDS:
        raise _err("GAP04-E0200", "lease envelope field set mismatch",
                   missing=sorted(LEASE_FIELDS - set(env)), unexpected=sorted(set(env) - LEASE_FIELDS))
    alg = env["alg"]
    if alg not in crypto.ALLOWED_SIG_ALGS:
        raise _err("GAP04-E0203", "algorithm not allowed", alg=alg)
    for f in ("issuer", "lease_id", "key_id", "trust_domain"):
        if not isinstance(env[f], str) or not ID_RE.match(env[f]):
            raise _err("GAP04-E0200", f"{f} malformed")
    if env["trust_domain"] != trust.trust_domain:
        raise _err("GAP04-E0204", "trust domain mismatch")
    key = trust.resolve(env["key_id"], env["issuer"], alg, "lease", now)
    payload = lease_payload(env)
    if not isinstance(env["sig"], str) or not crypto.verify(key.public_key, canonical.dumps(payload), env["sig"]):
        raise _err("GAP04-E0201", "lease signature invalid", lease_id=env["lease_id"])
    # --- authenticated from here on; now validate semantics ---
    scope = env["scope"]
    if not isinstance(scope, dict) or set(scope) != set(SCOPE_KEYS):
        raise _err("GAP04-E0200", "scope malformed")
    for k in SCOPE_KEYS:
        if scope.get(k) != expected_scope.get(k):
            raise _err("GAP04-E0204", "lease scope binding mismatch", field=k)
    issued, nbf, exp = _int(env, "issued_at"), _int(env, "not_before"), _int(env, "expires_at")
    if not (issued <= nbf < exp):
        raise _err("GAP04-E0205", "issued/not_before/expires ordering invalid")
    if exp - nbf > MAX_LEASE_LIFETIME_S:
        raise _err("GAP04-E0205", "lease lifetime exceeds maximum")
    if issued > now + MAX_CLOCK_SKEW_S:
        raise _err("GAP04-E0205", "lease issued in the future")
    if now + MAX_CLOCK_SKEW_S < nbf:
        raise _err("GAP04-E0205", "lease not yet valid")
    if now >= exp:
        raise _err("GAP04-E0205", "lease expired")
    epoch = _int(env, "authority_epoch")
    if epoch < max(1, min_authority_epoch):  # epoch 0 is reserved/never valid
        raise _err("GAP04-E0206", "stale authority epoch", epoch=epoch, watermark=min_authority_epoch)
    if env["lease_id"] in revoked_lease_ids:
        raise _err("GAP04-E0206", "lease revoked", lease_id=env["lease_id"])
    pol = env["policy"]
    if not isinstance(pol, dict) or set(pol) != {"version", "digest"} or not isinstance(pol["digest"], str) \
            or not DIGEST_RE.match(pol["digest"]) or not isinstance(pol["version"], int) or isinstance(pol["version"], bool):
        raise _err("GAP04-E0200", "policy binding malformed")
    if expected_policy_digest is not None and not crypto.ct_equal(pol["digest"], expected_policy_digest):
        raise _err("GAP04-E0207", "policy digest mismatch")
    caps = env["capabilities"]
    if not isinstance(caps, list) or caps != sorted(set(caps)) or not set(caps) <= CAPABILITIES:
        raise _err("GAP04-E0200", "capability set malformed")
    if not isinstance(env["nonce"], str) or not NONCE_RE.match(env["nonce"]):
        raise _err("GAP04-E0200", "nonce malformed")
    return VerifiedLease(env["lease_id"], crypto.fingerprint(canonical.dumps(env)), env["issuer"], env["key_id"],
                         dict(scope), issued, nbf, exp, pol["version"], pol["digest"], frozenset(caps), epoch, env["nonce"])


# ---------------------------------------------------------------- policy (C05)

POLICY_FIELDS = frozenset({"version", "issuer", "trust_domain", "policy_version", "activated_at", "author",
                           "approver", "rules", "key_id", "alg", "sig"})


@dataclass(frozen=True)
class VerifiedPolicy:
    policy_version: int
    digest: str
    issuer: str
    key_id: str
    activated_at: int
    author: str
    approver: str
    rules: Mapping[str, Any]


def policy_digest(bundle: Mapping[str, Any]) -> str:
    return canonical.digest({k: v for k, v in bundle.items() if k != "sig"})


def sign_policy(bundle: Mapping[str, Any], seed: bytes) -> dict:
    b = dict(bundle)
    b["sig"] = crypto.sign(seed, canonical.dumps(b))
    return b


def verify_policy(bundle: Mapping[str, Any], *, trust: TrustStore | None, now: int, min_policy_version: int) -> VerifiedPolicy:
    if trust is None:
        raise _err("GAP04-E0208", "trust store unavailable")
    crypto.require_backend()
    try:
        canonical.dumps(bundle)
    except canonical.CanonicalError as e:
        raise _err("GAP04-E0220", f"policy non-canonical: {e}") from None
    if bundle.get("version") != POLICY_VERSION or set(bundle) != POLICY_FIELDS:
        raise _err("GAP04-E0220", "policy bundle version/field set invalid")
    if bundle["trust_domain"] != trust.trust_domain:
        raise _err("GAP04-E0220", "policy trust domain mismatch")
    key = trust.resolve(bundle["key_id"], bundle["issuer"], bundle["alg"], "policy", now)
    body = {k: v for k, v in bundle.items() if k != "sig"}
    if not crypto.verify(key.public_key, canonical.dumps(body), bundle["sig"]):
        raise _err("GAP04-E0220", "policy signature invalid")
    pv = bundle["policy_version"]
    if not isinstance(pv, int) or isinstance(pv, bool) or pv < min_policy_version:
        raise _err("GAP04-E0221", "policy version rollback", version=pv, pinned=min_policy_version)
    if bundle["author"] == bundle["approver"]:
        raise _err("GAP04-E0220", "policy author and approver must differ")
    return VerifiedPolicy(pv, policy_digest(bundle), bundle["issuer"], bundle["key_id"], int(bundle["activated_at"]),
                          bundle["author"], bundle["approver"], dict(bundle["rules"]))
