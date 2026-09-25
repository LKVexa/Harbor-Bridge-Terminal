"""PK_SIGNATURE/3 - asymmetric, namespace-bound production signature envelope.

Envelope (all fields required; ``nonce`` may be null, ``refs`` may be empty)::

    {"v": 3, "alg", "kid", "signer", "tenant", "site", "env", "kind", "purpose",
     "policy_domain", "digest_alg", "digest", "issued_at", "nonce", "refs", "sig"}

Signed bytes = ``ld_encode("signature/3", fields-in-fixed-order)`` - domain
separated and length delimited, so no two semantic envelopes share signed
bytes.  ``sig`` is strict unpadded base64url.

Verification order (each failure has its own stable code):
parse/shape -> version -> namespace -> kind/purpose -> digest -> key id ->
certificate chain (trust generation) -> identity binding -> algorithm pinning
and downgrade -> signer authorisation -> freshness (trusted time) ->
cryptographic verification.  Evidence records the trust generation/digest.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from typing import Any, Mapping

from . import algorithms as algs
from .canonical import b64u_decode, b64u_encode, canonical_bytes, exact_fields, ld_encode, strict_loads
from .errors import GapError, fail
from .keys import KeyRef
from .trust import Namespace, TrustGeneration

SIGNATURE_V3 = 3
SIG_FIELDS = ("v", "alg", "kid", "signer", "tenant", "site", "env", "kind", "purpose", "policy_domain",
              "digest_alg", "digest", "issued_at", "nonce", "refs")
DIGEST_ALGS = {"sha256": 64, "sha512": 128}
KINDS = frozenset({"code", "policy", "grant", "label", "attestation", "bundle", "oci-image", "oci-index", "wasm-module",
                   "wasm-component", "microvm-image", "provider-bundle", "trust-config", "sbom"})
_HEX = re.compile(r"^[0-9a-f]+$")
MAX_ENVELOPE_BYTES = 16384


def signed_message(env: Mapping[str, Any]) -> bytes:
    fields = []
    for k in SIG_FIELDS:
        v = env[k]
        if k == "refs":
            v = canonical_bytes(list(v))
        fields.append((k, v))
    return ld_encode("signature/3", fields)


def artifact_digest(payload: bytes, alg: str = "sha256") -> str:
    return hashlib.new(alg, bytes(payload)).hexdigest()


class ArtifactSigner:
    """Signs through a KeyCustody; never sees private key bytes."""

    def __init__(self, custody: Any, ref: KeyRef, identity: str, *, audit: Any = None):
        self._custody = custody
        self.ref = ref
        self.identity = identity
        self._audit = audit

    def sign_digest(self, digest_hex: str, kind: str, *, now: int, policy_domain: str = "default",
                    digest_alg: str = "sha256", nonce: str | None = None, refs: list[str] | None = None,
                    purpose: str | None = None) -> dict[str, Any]:
        if kind not in KINDS:
            raise fail("POLICY_DENY", "unknown artifact kind", kind=kind)
        env = {"v": SIGNATURE_V3, "alg": self.ref.algorithm, "kid": self.ref.kid, "signer": self.identity,
               "tenant": self.ref.tenant, "site": self.ref.site, "env": self.ref.environment, "kind": kind,
               "purpose": purpose or f"sign:{kind}", "policy_domain": policy_domain, "digest_alg": digest_alg,
               "digest": digest_hex, "issued_at": int(now), "nonce": nonce, "refs": sorted(refs or [])}
        _shape(env)
        rid = str(uuid.uuid4())
        sig = self._custody.sign(self.ref, signed_message(env), request_id=rid)
        env["sig"] = b64u_encode(sig)
        if self._audit is not None:
            self._audit.append("artifact.sign.v3", {"kid": self.ref.kid, "kind": kind, "digest": digest_hex, "request_id": rid})
        return env

    def sign(self, payload: bytes, kind: str, *, now: int, **kw: Any) -> dict[str, Any]:
        return self.sign_digest(artifact_digest(payload, kw.get("digest_alg", "sha256")), kind, now=now, **kw)


def _shape(env: Mapping[str, Any]) -> None:
    if env.get("v") != SIGNATURE_V3:
        raise fail("ENVELOPE_VERSION_UNSUPPORTED", "signature envelope version not accepted", v=str(env.get("v"))[:16])
    for k in ("alg", "kid", "signer", "tenant", "site", "env", "kind", "purpose", "policy_domain", "digest_alg", "digest"):
        v = env[k]
        if not isinstance(v, str) or not v or len(v) > 512 or any(ord(c) < 0x20 for c in v):
            raise fail("ENVELOPE_MALFORMED", f"signature field {k} invalid", field=k)
    if isinstance(env["issued_at"], bool) or not isinstance(env["issued_at"], int) or env["issued_at"] < 0:
        raise fail("ENVELOPE_MALFORMED", "issued_at invalid", field="issued_at")
    if env["nonce"] is not None and (not isinstance(env["nonce"], str) or not 16 <= len(env["nonce"]) <= 128):
        raise fail("ENVELOPE_MALFORMED", "nonce invalid", field="nonce")
    if not isinstance(env["refs"], list) or len(env["refs"]) > 32 or not all(isinstance(r, str) and 0 < len(r) <= 256 for r in env["refs"]):
        raise fail("ENVELOPE_MALFORMED", "refs invalid", field="refs")
    if env["refs"] != sorted(env["refs"]) or len(set(env["refs"])) != len(env["refs"]):
        raise fail("ENVELOPE_MALFORMED", "refs must be sorted and unique", field="refs")
    n = DIGEST_ALGS.get(env["digest_alg"])
    if n is None:
        raise fail("ALG_UNSUPPORTED", "digest algorithm not accepted", digest_alg=env["digest_alg"])
    if len(env["digest"]) != n or _HEX.fullmatch(env["digest"]) is None:
        raise fail("ENVELOPE_MALFORMED", "digest encoding invalid", field="digest")


def parse_envelope(data: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(data, (bytes, str)):
        raw = data.encode() if isinstance(data, str) else data
        if len(raw) > MAX_ENVELOPE_BYTES:
            raise fail("INPUT_TOO_LARGE", "signature envelope too large")
        obj = strict_loads(raw)
        if canonical_bytes(obj) != raw:
            raise fail("ENVELOPE_MALFORMED", "signature envelope is not canonically encoded")
    else:
        obj = data
    if isinstance(obj, Mapping):
        if obj.get("schema") in ("PK_SIGNATURE/1", "PK_SIGNATURE/2"):
            raise fail("ENVELOPE_VERSION_UNSUPPORTED", "legacy signature envelope rejected by production verifier", schema=obj.get("schema"))
    env = dict(exact_fields(obj, set(SIG_FIELDS) | {"sig"}, what="PK_SIGNATURE/3"))
    _shape(env)
    return env


def verify_signature(envelope: bytes | str | Mapping[str, Any], *, digest_hex: str, kind: str, trust: TrustGeneration,
                     now: int, policy_domain: str = "default", max_age_s: int | None = None,
                     max_future_skew_s: int = 300, profile: str = algs.PROFILE_PRODUCTION) -> dict[str, Any]:
    env = parse_envelope(envelope)
    ns = trust.namespace
    if (env["tenant"], env["site"], env["env"]) != (ns.tenant, ns.site, ns.environment):
        raise fail("TENANT_MISMATCH", "signature bound to another tenant/site/environment",
                   signature_namespace=[env["tenant"], env["site"], env["env"]], verifier_namespace=ns.as_dict())
    if env["kind"] != kind:
        raise fail("SIGNATURE_INVALID", "signature is bound to a different artifact kind", signature_kind=env["kind"], requested_kind=kind)
    if env["purpose"] != f"sign:{kind}":
        raise fail("CERT_USAGE", "signature purpose does not match artifact kind", purpose=env["purpose"])
    if env["policy_domain"] != policy_domain:
        raise fail("SIGNATURE_INVALID", "signature bound to another policy domain", signature_domain=env["policy_domain"], requested=policy_domain)
    if not hmac.compare_digest(env["digest"], str(digest_hex)):
        raise fail("SIGNATURE_INVALID", "digest mismatch", signed_digest=env["digest"], actual_digest=str(digest_hex)[:128])
    trust.check_fresh(now)
    ident = trust.resolve_kid(env["kid"], now, purpose=env["purpose"], profile=profile)
    if ident.identity != env["signer"]:
        raise fail("IDENTITY_MISMATCH", "envelope signer does not match certificate identity", kid=env["kid"])
    if env["alg"] != ident.alg:
        raise fail("ALG_DOWNGRADE", "envelope algorithm differs from the key's certified algorithm", envelope_alg=env["alg"], key_alg=ident.alg)
    authz = trust.signer(ident.identity)
    if kind not in authz.kinds:
        raise fail("SIGNER_UNTRUSTED", "identity not authorised for artifact kind", identity=ident.identity, kind=kind)
    algs.check_not_downgrade(env["alg"], authz.algorithms, authz.min_strength)
    if env["issued_at"] > now + max_future_skew_s:
        raise fail("SIGNATURE_FUTURE", "signature issued in the future", issued_at=env["issued_at"], now=now)
    if max_age_s is not None and now - env["issued_at"] > max_age_s:
        raise fail("SIGNATURE_EXPIRED", "signature exceeds maximum age", issued_at=env["issued_at"], now=now, max_age_s=max_age_s)
    algs.verify_raw(env["alg"], ident.spki, b64u_decode(env["sig"], max_len=1400), signed_message(env), profile=profile, now=now)
    return {
        "schema": "PK_VERIFICATION/3", "verified": True, "kind": kind, "digest_alg": env["digest_alg"], "digest": env["digest"],
        "alg": env["alg"], "kid": env["kid"], "signer": ident.identity, "roles": sorted(authz.roles),
        "issued_at": env["issued_at"], "policy_domain": policy_domain, "envelope_digest": hashlib.sha256(canonical_bytes(env)).hexdigest(),
        "trust": ident.evidence(), "profile": profile,
    }


def verify_legacy_v2_reference(sig: Mapping[str, Any], payload: bytes, kind: str, store: Any, *, migration_approval: Mapping[str, Any],
                               audit: Any) -> dict[str, Any]:
    """Explicit, audited migration verifier for v5 ``PK_SIGNATURE/2`` (HMAC reference).

    Result carries ``profile: reference`` which production admission refuses;
    it exists only so migration tooling can re-sign v5 artifacts under v3.
    """
    exact_fields(migration_approval, {"approval_id", "approved_by", "expires"}, what="migration approval")
    if audit is None:
        raise fail("POLICY_INVALID", "legacy verification requires an audit ledger")
    audit.append("legacy.v2.verify_attempt", {"approval_id": migration_approval["approval_id"], "kind": kind})
    try:
        res = store.verify(sig, payload, kind)
    except GapError:
        raise
    return {**res, "profile": algs.PROFILE_REFERENCE, "migration_approval": migration_approval["approval_id"]}
