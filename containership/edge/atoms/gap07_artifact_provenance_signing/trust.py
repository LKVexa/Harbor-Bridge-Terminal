"""Public-key / certificate trust model (v6).

Trust is expressed as an immutable ``TrustGeneration`` scoped to one namespace
(tenant/site/environment) with a monotonic ``generation`` number.  It contains

* ``anchors``     - root public keys (id, alg, SPKI, validity, name constraints,
                    max path length, state active|retired);
* ``certs``       - ``PK_CERT/1`` identity certificates (intermediates carry the
                    ``ca`` usage) forming chains to an anchor;
* ``signers``     - authorisation policy per identity (roles, artifact kinds,
                    attestation predicate types, algorithms);
* ``revoked``     - revoked certificate serials, key ids and identities.

Identity is the certificate ``subject`` URI (e.g. ``spiffe://acme/prod/release-bot``);
display names are never authorising.  Chain building is bounded (depth, pool
size) and deterministic: every candidate path is validated with *all*
constraints on that path, and when several succeed the lexicographically
smallest (anchor id, serials) is chosen and recorded - an alternate path can
never broaden what the configured anchors permit.

Optional X.509 interop: ``validate_x509`` delegates path building to
``cryptography.x509.verification`` (Rust webpki-derived) with an EKU=codeSigning
end-entity policy and extracts the URI SAN as the identity.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from . import algorithms as algs
from .canonical import b64u_decode, b64u_encode, canonical_bytes, exact_fields, ld_encode
from .errors import GapError, fail

CERT_SCHEMA = "PK_CERT/1"
TRUST_SCHEMA = "PK_TRUST_GENERATION/1"
MAX_CHAIN = 5
MAX_POOL = 2048
CLOCK_SKEW_S = 60


@dataclass(frozen=True)
class Namespace:
    tenant: str
    site: str
    environment: str

    def as_dict(self) -> dict[str, str]:
        return {"tenant": self.tenant, "site": self.site, "environment": self.environment}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Namespace":
        d = exact_fields(d, {"tenant", "site", "environment"}, what="namespace")
        for v in d.values():
            if not isinstance(v, str) or not v or len(v) > 128 or "/" in v:
                raise fail("ENVELOPE_MALFORMED", "namespace component invalid")
        return cls(d["tenant"], d["site"], d["environment"])

    def covers(self, other: "Namespace") -> bool:
        return all(a in ("*", b) for a, b in ((self.tenant, other.tenant), (self.site, other.site), (self.environment, other.environment)))


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    alg: str
    spki: bytes
    not_before: int
    not_after: int
    state: str = "active"            # active | retired
    name_constraints: tuple[str, ...] = ()   # permitted identity prefixes; empty = any
    max_path_len: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {"anchor_id": self.anchor_id, "alg": self.alg, "spki": b64u_encode(self.spki), "not_before": self.not_before,
                "not_after": self.not_after, "state": self.state, "name_constraints": list(self.name_constraints), "max_path_len": self.max_path_len}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Anchor":
        d = exact_fields(d, {"anchor_id", "alg", "spki", "not_before", "not_after", "state", "name_constraints", "max_path_len"}, what="anchor")
        if d["state"] not in ("active", "retired"):
            raise fail("ENVELOPE_MALFORMED", "anchor state invalid")
        return cls(d["anchor_id"], d["alg"], b64u_decode(d["spki"]), int(d["not_before"]), int(d["not_after"]), d["state"],
                   tuple(d["name_constraints"]), int(d["max_path_len"]))


_CERT_FIELDS = ("schema", "serial", "issuer", "subject", "namespace", "kid", "alg", "spki", "usages",
                "path_len", "name_constraints", "not_before", "not_after", "sig_alg")


def _cert_message(body: Mapping[str, Any]) -> bytes:
    return ld_encode("cert/1", [(k, canonical_bytes(body[k]) if isinstance(body[k], (list, dict)) else body[k]) for k in _CERT_FIELDS])


def issue_cert(*, issuer_id: str, issuer_alg: str, issuer_sign, serial: str, subject: str, namespace: Namespace,
               kid: str, alg: str, spki: bytes, usages: Sequence[str], not_before: int, not_after: int,
               path_len: int = 0, name_constraints: Sequence[str] = ()) -> dict[str, Any]:
    body = {"schema": CERT_SCHEMA, "serial": serial, "issuer": issuer_id, "subject": subject, "namespace": namespace.as_dict(),
            "kid": kid, "alg": alg, "spki": b64u_encode(spki), "usages": sorted(set(usages)), "path_len": path_len,
            "name_constraints": sorted(name_constraints), "not_before": not_before, "not_after": not_after, "sig_alg": issuer_alg}
    return {**body, "sig": b64u_encode(issuer_sign(_cert_message(body)))}


_URI = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s/?#]+(/[^\s?#]*)?$")


def _check_subject(subject: str) -> None:
    """Identity URIs must be normalised: no dot/empty segments, no percent-encoding, no query/fragment."""
    if _URI.fullmatch(subject) is None or "%" in subject or "\\" in subject:
        raise fail("ENVELOPE_MALFORMED", "certificate subject is not a normalised identity URI")
    path = subject.split("://", 1)[1].split("/")[1:]
    if any(seg in ("", ".", "..") for seg in path[:-1]) or (path and path[-1] in (".", "..")):
        raise fail("ENVELOPE_MALFORMED", "certificate subject contains dot or empty path segments")


def _within(subject: str, prefix: str) -> bool:
    """Segment-wise name-constraint match (``spiffe://acme/prod`` does not permit ``.../prod-evil``)."""
    p = prefix.rstrip("/")
    return subject == p or subject.startswith(p + "/")


def parse_cert(d: Mapping[str, Any]) -> dict[str, Any]:
    d = exact_fields(d, set(_CERT_FIELDS) | {"sig"}, what="certificate")
    if d["schema"] != CERT_SCHEMA:
        raise fail("ENVELOPE_VERSION_UNSUPPORTED", "unsupported certificate schema")
    for k in ("serial", "issuer", "subject", "kid", "alg", "sig_alg"):
        if not isinstance(d[k], str) or not d[k] or len(d[k]) > 512:
            raise fail("ENVELOPE_MALFORMED", f"certificate field {k} invalid")
    for k in ("not_before", "not_after", "path_len"):
        if isinstance(d[k], bool) or not isinstance(d[k], int) or d[k] < 0:
            raise fail("ENVELOPE_MALFORMED", f"certificate field {k} invalid")
    if not isinstance(d["usages"], list) or not all(isinstance(u, str) for u in d["usages"]) or len(d["usages"]) > 64:
        raise fail("ENVELOPE_MALFORMED", "certificate usages invalid")
    Namespace.from_dict(d["namespace"])
    _check_subject(d["subject"])
    if not isinstance(d["name_constraints"], list) or not all(isinstance(x, str) for x in d["name_constraints"]):
        raise fail("ENVELOPE_MALFORMED", "certificate name constraints invalid")
    b64u_decode(d["spki"])
    b64u_decode(d["sig"])
    return dict(d)


@dataclass(frozen=True)
class SignerAuthz:
    identity: str
    roles: frozenset[str]
    kinds: frozenset[str]
    predicate_types: frozenset[str] = frozenset()
    algorithms: frozenset[str] = frozenset({"ed25519", "ecdsa-p256-sha256", "ecdsa-p384-sha384", "rsa-pss-sha256-3072", "rsa-pss-sha384-4096"})
    min_strength: int = 128

    def to_dict(self) -> dict[str, Any]:
        return {"identity": self.identity, "roles": sorted(self.roles), "kinds": sorted(self.kinds),
                "predicate_types": sorted(self.predicate_types), "algorithms": sorted(self.algorithms), "min_strength": self.min_strength}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SignerAuthz":
        d = exact_fields(d, {"identity", "roles", "kinds", "predicate_types", "algorithms", "min_strength"}, what="signer")
        return cls(d["identity"], frozenset(d["roles"]), frozenset(d["kinds"]), frozenset(d["predicate_types"]),
                   frozenset(d["algorithms"]), int(d["min_strength"]))


@dataclass(frozen=True)
class ValidatedIdentity:
    identity: str
    kid: str
    alg: str
    spki: bytes
    namespace: Namespace
    usages: frozenset[str]
    path: tuple[str, ...]      # anchor_id, then serials root->leaf
    generation: int
    trust_digest: str

    def evidence(self) -> dict[str, Any]:
        return {"identity": self.identity, "kid": self.kid, "alg": self.alg, "path": list(self.path),
                "trust_generation": self.generation, "trust_digest": self.trust_digest, "namespace": self.namespace.as_dict()}


@dataclass(frozen=True)
class TrustGeneration:
    namespace: Namespace
    generation: int
    issued_at: int
    max_staleness_s: int
    anchors: tuple[Anchor, ...]
    certs: tuple[Mapping[str, Any], ...]
    signers: tuple[SignerAuthz, ...]
    revoked_serials: frozenset[str] = frozenset()
    revoked_kids: frozenset[str] = frozenset()
    revoked_identities: frozenset[str] = frozenset()
    policy_ref: str = ""
    _index: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.certs) > MAX_POOL or len(self.anchors) > 256 or len(self.signers) > MAX_POOL:
            raise fail("INPUT_TOO_LARGE", "trust generation exceeds entry bounds")
        ids = [a.anchor_id for a in self.anchors]
        serials = [c["serial"] for c in self.certs]
        kids = [c["kid"] for c in self.certs if "ca" not in c["usages"]]
        if len(set(ids)) != len(ids) or len(set(serials)) != len(serials):
            raise fail("TRUST_CORRUPT", "duplicate anchor id or certificate serial")
        if len(set(kids)) != len(kids):
            raise fail("KEY_ID_COLLISION", "duplicate key id across leaf certificates")
        for c in self.certs:
            parse_cert(c)
            ns = Namespace.from_dict(c["namespace"])
            if "ca" not in c["usages"] and ns != self.namespace:
                raise fail("TRUST_SCOPE", "leaf certificate namespace differs from trust generation", serial=c["serial"])
            if "ca" not in c["usages"] and not c["kid"].startswith(f"{ns.tenant}/{ns.site}/{ns.environment}/"):
                raise fail("KEY_ID_COLLISION", "leaf kid is not namespace-qualified", kid=c["kid"])
        self._index.update(
            anchors={a.anchor_id: a for a in self.anchors},
            by_serial={c["serial"]: c for c in self.certs},
            by_kid={c["kid"]: c for c in self.certs if "ca" not in c["usages"]},
            signers={s.identity: s for s in self.signers},
        )

    # serialisation ------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRUST_SCHEMA, "namespace": self.namespace.as_dict(), "generation": self.generation,
            "issued_at": self.issued_at, "max_staleness_s": self.max_staleness_s,
            "anchors": [a.to_dict() for a in sorted(self.anchors, key=lambda a: a.anchor_id)],
            "certs": sorted((dict(c) for c in self.certs), key=lambda c: c["serial"]),
            "signers": [s.to_dict() for s in sorted(self.signers, key=lambda s: s.identity)],
            "revoked_serials": sorted(self.revoked_serials), "revoked_kids": sorted(self.revoked_kids),
            "revoked_identities": sorted(self.revoked_identities), "policy_ref": self.policy_ref,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "TrustGeneration":
        d = exact_fields(d, {"schema", "namespace", "generation", "issued_at", "max_staleness_s", "anchors", "certs", "signers",
                             "revoked_serials", "revoked_kids", "revoked_identities", "policy_ref"}, what="trust generation")
        if d["schema"] != TRUST_SCHEMA:
            raise fail("ENVELOPE_VERSION_UNSUPPORTED", "unsupported trust generation schema")
        for k in ("generation", "issued_at", "max_staleness_s"):
            if isinstance(d[k], bool) or not isinstance(d[k], int) or d[k] < 0:
                raise fail("TRUST_CORRUPT", f"trust field {k} invalid")
        return cls(Namespace.from_dict(d["namespace"]), d["generation"], d["issued_at"], d["max_staleness_s"],
                   tuple(Anchor.from_dict(a) for a in d["anchors"]), tuple(parse_cert(c) for c in d["certs"]),
                   tuple(SignerAuthz.from_dict(s) for s in d["signers"]), frozenset(d["revoked_serials"]),
                   frozenset(d["revoked_kids"]), frozenset(d["revoked_identities"]), str(d["policy_ref"]))

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_bytes(self.to_dict())).hexdigest()

    # evaluation ---------------------------------------------------------
    def check_fresh(self, now: int) -> None:
        if self.issued_at > now + CLOCK_SKEW_S * 5:
            raise fail("TRUST_CORRUPT", "trust generation issued in the future", issued_at=self.issued_at, now=now)
        if now - self.issued_at > self.max_staleness_s:
            raise fail("TRUST_STALE", "trust generation exceeds staleness budget", generation=self.generation,
                       issued_at=self.issued_at, max_staleness_s=self.max_staleness_s)

    def signer(self, identity: str) -> SignerAuthz:
        s = self._index["signers"].get(identity)
        if s is None:
            raise fail("SIGNER_UNTRUSTED", "identity has no authorisation in this trust generation", identity=identity[:256])
        return s

    def resolve_kid(self, kid: str, now: int, *, purpose: str, profile: str = algs.PROFILE_PRODUCTION) -> ValidatedIdentity:
        """Validate the leaf cert for ``kid`` to an anchor and return the bound identity."""
        leaf = self._index["by_kid"].get(kid)
        if leaf is None:
            raise fail("SIGNER_UNTRUSTED", "no certificate for key id in this trust generation", kid=kid[:256])
        return self.validate_leaf(leaf, now, purpose=purpose, profile=profile)

    def validate_leaf(self, leaf: Mapping[str, Any], now: int, *, purpose: str, profile: str = algs.PROFILE_PRODUCTION) -> ValidatedIdentity:
        leaf = parse_cert(leaf)
        if "ca" in leaf["usages"]:
            raise fail("CERT_USAGE", "CA certificate cannot sign artifacts")
        ns = Namespace.from_dict(leaf["namespace"])
        if ns != self.namespace:
            raise fail("TENANT_MISMATCH", "certificate namespace differs from verifier namespace",
                       cert_namespace=ns.as_dict(), verifier_namespace=self.namespace.as_dict())
        if purpose not in leaf["usages"]:
            raise fail("CERT_USAGE", "certificate does not permit this purpose", purpose=purpose)
        errors: list[GapError] = []
        good: list[tuple[str, ...]] = []
        for path in self._paths(leaf):
            try:
                self._validate_path(path, leaf, now, profile)
                good.append(path)
            except GapError as exc:
                errors.append(exc)
        if not good:
            if not errors:
                raise fail("CHAIN_UNTRUSTED", "no path from certificate to a configured anchor", serial=leaf["serial"])
            raise sorted(errors, key=lambda e: _SPECIFICITY.get(e.code, 99))[0]
        path = min(good)
        return ValidatedIdentity(leaf["subject"], leaf["kid"], leaf["alg"], b64u_decode(leaf["spki"]), ns,
                                 frozenset(leaf["usages"]), path, self.generation, self.digest)

    def _paths(self, leaf: Mapping[str, Any]) -> Iterable[tuple[str, ...]]:
        """Yield (anchor_id, serial..., leaf_serial) candidate paths, bounded."""
        out: list[tuple[str, ...]] = []

        def walk(cert: Mapping[str, Any], acc: tuple[str, ...], depth: int) -> None:
            if depth > MAX_CHAIN or len(out) > 64:
                return
            issuer = cert["issuer"]
            if issuer in self._index["anchors"]:
                out.append((issuer,) + acc)
            parent = self._index["by_serial"].get(issuer)
            if parent is not None and "ca" in parent["usages"] and parent["serial"] not in acc:
                walk(parent, (parent["serial"],) + acc, depth + 1)

        walk(leaf, (leaf["serial"],), 1)
        return out

    def _validate_path(self, path: tuple[str, ...], leaf: Mapping[str, Any], now: int, profile: str) -> None:
        anchor = self._index["anchors"][path[0]]
        if anchor.state != "active":
            raise fail("CHAIN_UNTRUSTED", "anchor is retired", anchor=anchor.anchor_id)
        if not anchor.not_before - CLOCK_SKEW_S <= now <= anchor.not_after + CLOCK_SKEW_S:
            raise fail("CERT_EXPIRED" if now > anchor.not_after else "CERT_NOT_YET_VALID", "anchor outside validity", anchor=anchor.anchor_id)
        # intermediates come from the pool; the leaf is ALWAYS the caller's object so its own
        # signature is verified (a forged leaf reusing a pooled serial cannot borrow its chain)
        certs = [self._index["by_serial"].get(s) for s in path[1:-1]] + [leaf]
        if any(c is None for c in certs) or any("ca" not in c["usages"] for c in certs[:-1]):
            raise fail("CHAIN_UNTRUSTED", "path references unknown certificate")
        if len(certs) - 1 > anchor.max_path_len:
            raise fail("PATH_LENGTH", "chain longer than anchor path-length", anchor=anchor.anchor_id)
        issuer_alg, issuer_spki, issuer_id = anchor.alg, anchor.spki, anchor.anchor_id
        constraints = [tuple(anchor.name_constraints)]
        remaining = anchor.max_path_len
        for i, cert in enumerate(certs):
            is_leaf = i == len(certs) - 1
            if cert["issuer"] != issuer_id:
                raise fail("CHAIN_UNTRUSTED", "issuer linkage broken")
            if cert["sig_alg"] != issuer_alg:
                raise fail("ALG_DOWNGRADE", "certificate signature algorithm differs from issuer key algorithm", serial=cert["serial"])
            algs.verify_raw(issuer_alg, issuer_spki, b64u_decode(cert["sig"]), _cert_message(cert), profile=profile, now=now)
            algs.get(cert["alg"], profile=profile, now=now)
            if cert["serial"] in self.revoked_serials or cert["kid"] in self.revoked_kids:
                raise fail("CERT_REVOKED", "certificate or key revoked", serial=cert["serial"])
            if now > cert["not_after"] + CLOCK_SKEW_S:
                raise fail("CERT_EXPIRED", "certificate expired", serial=cert["serial"])
            if now < cert["not_before"] - CLOCK_SKEW_S:
                raise fail("CERT_NOT_YET_VALID", "certificate not yet valid", serial=cert["serial"])
            for nc in constraints:
                if nc and not any(_within(cert["subject"], p) for p in nc):
                    raise fail("NAME_CONSTRAINT", "subject outside issuer name constraints", serial=cert["serial"])
            if not is_leaf:
                if "ca" not in cert["usages"]:
                    raise fail("CERT_USAGE", "non-CA certificate used as issuer", serial=cert["serial"])
                remaining -= 1
                if remaining < 0 or cert["path_len"] < len(certs) - i - 2:
                    raise fail("PATH_LENGTH", "path-length constraint exceeded", serial=cert["serial"])
                constraints.append(tuple(cert["name_constraints"]))
            issuer_alg, issuer_spki, issuer_id = cert["alg"], b64u_decode(cert["spki"]), cert["serial"]
        if leaf["subject"] in self.revoked_identities:
            raise fail("CERT_REVOKED", "identity revoked", identity=leaf["subject"][:256])

    def trust_report(self, kid: str, now: int, purpose: str) -> dict[str, Any]:
        """Human/machine-readable explanation without credential material."""
        try:
            v = self.resolve_kid(kid, now, purpose=purpose)
            return {"kid": kid, "result": "trusted", **v.evidence()}
        except GapError as exc:
            return {"kid": kid, "result": "refused", "code": exc.code, "reason": str(exc), "trust_generation": self.generation}


_SPECIFICITY = {"CERT_REVOKED": 0, "CERT_EXPIRED": 1, "CERT_NOT_YET_VALID": 2, "NAME_CONSTRAINT": 3, "PATH_LENGTH": 4,
                "CERT_USAGE": 5, "ALG_DOWNGRADE": 6, "ALG_DEPRECATED": 7, "ALG_REFERENCE_ONLY": 8, "SIGNATURE_INVALID": 9, "CHAIN_UNTRUSTED": 10}


# ------------------------------------------------------------------ X.509

def validate_x509(leaf_der: bytes, intermediates_der: Sequence[bytes], anchors_der: Sequence[bytes], now: int,
                  *, max_depth: int = 4) -> dict[str, Any]:
    """Validate an X.509 code-signing chain; return identity (URI SAN) + SPKI."""
    import datetime

    from cryptography import x509
    from cryptography.x509.oid import ExtendedKeyUsageOID
    from cryptography.x509.verification import Criticality, ExtensionPolicy, PolicyBuilder, Store, VerificationError as XVE

    if len(leaf_der) > 16384 or len(intermediates_der) > MAX_CHAIN or any(len(c) > 16384 for c in intermediates_der):
        raise fail("INPUT_TOO_LARGE", "X.509 chain exceeds bounds")
    try:
        leaf = x509.load_der_x509_certificate(leaf_der)
        inter = [x509.load_der_x509_certificate(c) for c in intermediates_der]
        roots = [x509.load_der_x509_certificate(c) for c in anchors_der]
    except ValueError as exc:
        raise fail("ENVELOPE_MALFORMED", "X.509 certificate is not valid DER") from exc

    def _eku(policy, cert, eku):
        if eku is None or ExtendedKeyUsageOID.CODE_SIGNING not in eku:
            raise ValueError("EKU codeSigning required")

    ee = ExtensionPolicy.webpki_defaults_ee().require_present(x509.ExtendedKeyUsage, Criticality.AGNOSTIC, _eku)
    ca = ExtensionPolicy.webpki_defaults_ca()
    verifier = (PolicyBuilder().store(Store(roots)).time(datetime.datetime.fromtimestamp(now, datetime.timezone.utc))
                .max_chain_depth(max_depth).extension_policies(ca_policy=ca, ee_policy=ee).build_client_verifier())
    try:
        verified = verifier.verify(leaf, inter)
    except XVE as exc:
        msg = str(exc).lower()
        code = "CERT_EXPIRED" if "expired" in msg or "not valid after" in msg else "CERT_USAGE" if "eku" in msg or "extension" in msg else "CHAIN_UNTRUSTED"
        raise fail(code, "X.509 chain validation failed", reason=str(exc)[:200]) from exc
    uris = [n for n in (verified.subjects or []) if isinstance(n, x509.UniformResourceIdentifier)]
    if len(uris) != 1:
        raise fail("IDENTITY_MISMATCH", "code-signing certificate must carry exactly one URI SAN identity")
    return {"identity": uris[0].value, "spki": algs.spki(leaf.public_key()),
            "chain": [c.fingerprint(__import__("cryptography.hazmat.primitives.hashes", fromlist=["SHA256"]).SHA256()).hex() for c in verified.chain]}
