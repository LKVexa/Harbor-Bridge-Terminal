"""DSSE v1 / in-toto Statement v1 / SLSA Provenance v1 attestation support.

* DSSE pre-authentication encoding (PAE) exactly as specified:
  ``"DSSEv1" SP LEN(type) SP type SP LEN(body) SP body``.
  Signatures are verified over PAE of the *original* payload bytes; the payload
  is parsed (strictly) only after a signature verifies, and never re-serialised
  before verification.  Original bytes are retained for evidence.
* Accepted payloadType: ``application/vnd.in-toto+json``.
* Accepted statement ``_type``: ``https://in-toto.io/Statement/v1``.
* Predicate types are allow-listed by policy; unknown types are refused
  before the predicate is parsed.  Built-in validator: SLSA Provenance v1.
* A DSSE ``keyid`` is a GAP-07 namespace-qualified kid resolved through the
  trust generation with purpose ``attest:<predicateType>`` - a release signer
  does not automatically authorise arbitrary predicates.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from . import algorithms as algs
from .canonical import b64_std_decode, exact_fields, strict_loads
from .errors import GapError, fail
from .trust import TrustGeneration

PAYLOAD_TYPE = "application/vnd.in-toto+json"
STATEMENT_V1 = "https://in-toto.io/Statement/v1"
SLSA_V1 = "https://slsa.dev/provenance/v1"
MAX_PAYLOAD = 1024 * 1024
MAX_SIGS = 16
MAX_SUBJECTS = 256


def pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode("utf-8")
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def make_envelope(statement_bytes: bytes, signers: Sequence[tuple[str, Callable[[bytes], bytes]]]) -> dict[str, Any]:
    msg = pae(PAYLOAD_TYPE, statement_bytes)
    return {"payloadType": PAYLOAD_TYPE, "payload": base64.b64encode(statement_bytes).decode(),
            "signatures": [{"keyid": kid, "sig": base64.b64encode(sign(msg)).decode()} for kid, sign in signers]}


def statement(subjects: Sequence[tuple[str, str]], predicate_type: str, predicate: Mapping[str, Any]) -> dict[str, Any]:
    return {"_type": STATEMENT_V1, "subject": [{"name": n, "digest": {"sha256": d}} for n, d in subjects],
            "predicateType": predicate_type, "predicate": dict(predicate)}


@dataclass(frozen=True)
class AttestationPolicy:
    predicate_types: frozenset[str] = frozenset({SLSA_V1})
    builder_ids: frozenset[str] = frozenset()
    build_types: frozenset[str] = frozenset()
    external_parameter_keys: frozenset[str] | None = None   # allowlist; None = unrestricted
    require_resolved_dependencies: bool = True
    max_age_s: int | None = None
    threshold: int = 1


@dataclass
class VerifiedAttestation:
    predicate_type: str
    subjects: dict[str, str]
    predicate: Mapping[str, Any]
    signers: list[dict[str, Any]]
    payload_sha256: str
    original_payload: bytes = field(repr=False)

    def evidence(self) -> dict[str, Any]:
        return {"predicate_type": self.predicate_type, "subjects": dict(self.subjects), "payload_sha256": self.payload_sha256,
                "signers": self.signers, "builder_id": _get(self.predicate, "runDetails", "builder", "id"),
                "build_type": _get(self.predicate, "buildDefinition", "buildType")}


def _get(d: Any, *path: str) -> Any:
    for p in path:
        if not isinstance(d, Mapping):
            return None
        d = d.get(p)
    return d


def verify_envelope(envelope: Mapping[str, Any], *, artifact_digest: str, trust: TrustGeneration, now: int,
                    policy: AttestationPolicy, profile: str = algs.PROFILE_PRODUCTION) -> VerifiedAttestation:
    env = exact_fields(envelope, {"payloadType", "payload", "signatures"}, what="DSSE envelope")
    if env["payloadType"] != PAYLOAD_TYPE:
        raise fail("ATTESTATION_INVALID", "unsupported DSSE payloadType", payload_type=str(env["payloadType"])[:64])
    payload = b64_std_decode(env["payload"], max_len=MAX_PAYLOAD * 2)
    if len(payload) > MAX_PAYLOAD:
        raise fail("INPUT_TOO_LARGE", "attestation payload too large")
    sigs = env["signatures"]
    if not isinstance(sigs, list) or not 1 <= len(sigs) <= MAX_SIGS:
        raise fail("ATTESTATION_INVALID", "DSSE signatures must be 1..16 entries")
    # predicate type must be policy-allowed before the predicate is interpreted;
    # peek at it only via strict parse, and verify signatures over raw bytes first.
    msg = pae(PAYLOAD_TYPE, payload)
    verified: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    errors: list[GapError] = []
    stmt = strict_loads(payload)
    if not isinstance(stmt, Mapping) or stmt.get("_type") != STATEMENT_V1:
        raise fail("ATTESTATION_INVALID", "unsupported in-toto statement type")
    ptype = stmt.get("predicateType")
    if ptype not in policy.predicate_types:
        raise fail("ATTESTATION_PREDICATE", "predicate type not allowed by policy", predicate_type=str(ptype)[:128])
    trust.check_fresh(now)
    for entry in sigs:
        e = exact_fields(entry, {"keyid", "sig"}, what="DSSE signature")
        try:
            ident = trust.resolve_kid(e["keyid"], now, purpose=f"attest:{ptype}", profile=profile)
            authz = trust.signer(ident.identity)
            if ptype not in authz.predicate_types:
                raise fail("SIGNER_UNTRUSTED", "identity not authorised for predicate type", identity=ident.identity)
            algs.check_not_downgrade(ident.alg, authz.algorithms, authz.min_strength)
            algs.verify_raw(ident.alg, ident.spki, b64_std_decode(e["sig"], max_len=2048), msg, profile=profile, now=now)
        except GapError as exc:
            errors.append(exc)
            continue
        if ident.identity in seen_ids:
            continue  # the same identity counts once toward thresholds
        seen_ids.add(ident.identity)
        verified.append(ident.evidence())
    if len(verified) < policy.threshold:
        if errors and not verified:
            raise errors[0]
        raise fail("THRESHOLD_UNMET", "not enough distinct valid attestation signers", have=len(verified), need=policy.threshold)

    st = exact_fields(stmt, {"_type", "subject", "predicateType", "predicate"}, what="in-toto statement")
    subjects = st["subject"]
    if not isinstance(subjects, list) or not 1 <= len(subjects) <= MAX_SUBJECTS:
        raise fail("ATTESTATION_INVALID", "statement subject list invalid")
    digests: dict[str, str] = {}
    for s in subjects:
        s = exact_fields(s, {"name", "digest"}, set(), what="subject")
        dg = exact_fields(s["digest"], set(), {"sha256", "sha512"}, what="subject digest")
        if not isinstance(s["name"], str) or not 0 < len(s["name"]) <= 1024:
            raise fail("ATTESTATION_SUBJECT", "subject name must be a non-empty string")
        if not isinstance(dg.get("sha256"), str) or len(dg["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in dg["sha256"]):
            raise fail("ATTESTATION_SUBJECT", "subject sha256 must be 64 lowercase hex characters")
        if "sha256" not in dg:
            raise fail("ATTESTATION_SUBJECT", "subject lacks sha256 digest")
        if s["name"] in digests or dg["sha256"] in digests.values():
            raise fail("ATTESTATION_SUBJECT", "duplicate/ambiguous subject entries")
        digests[s["name"]] = dg["sha256"]
    if sum(1 for d in digests.values() if hmac.compare_digest(d, artifact_digest)) != 1:
        raise fail("ATTESTATION_SUBJECT", "attestation subject does not match admitted artifact digest", artifact_digest=artifact_digest)
    pred = st["predicate"]
    if not isinstance(pred, Mapping):
        raise fail("ATTESTATION_INVALID", "predicate must be an object")
    if ptype == SLSA_V1:
        _validate_slsa(pred, policy, now)
    return VerifiedAttestation(ptype, digests, pred, verified, hashlib.sha256(payload).hexdigest(), payload)


def _validate_slsa(pred: Mapping[str, Any], policy: AttestationPolicy, now: int) -> None:
    p = exact_fields(pred, {"buildDefinition", "runDetails"}, what="SLSA predicate")
    bd = exact_fields(p["buildDefinition"], {"buildType", "externalParameters"}, {"internalParameters", "resolvedDependencies"}, what="buildDefinition")
    rd = exact_fields(p["runDetails"], {"builder"}, {"metadata", "byproducts"}, what="runDetails")
    builder = exact_fields(rd["builder"], {"id"}, {"version", "builderDependencies"}, what="builder")
    if policy.builder_ids and builder["id"] not in policy.builder_ids:
        raise fail("ATTESTATION_BUILDER", "builder identity not allowed", builder_id=str(builder["id"])[:256])
    if policy.build_types and bd["buildType"] not in policy.build_types:
        raise fail("ATTESTATION_BUILDER", "build type not allowed", build_type=str(bd["buildType"])[:256])
    ext = bd["externalParameters"]
    if not isinstance(ext, Mapping):
        raise fail("ATTESTATION_MATERIALS", "externalParameters must be an object")
    if policy.external_parameter_keys is not None:
        extra = sorted(set(ext) - policy.external_parameter_keys)
        if extra:
            raise fail("ATTESTATION_MATERIALS", "external parameters outside allowlist", keys=extra[:16])
    deps = bd.get("resolvedDependencies")
    if policy.require_resolved_dependencies and not deps:
        raise fail("ATTESTATION_MATERIALS", "resolvedDependencies required by policy")
    uris: set[str] = set()
    for dep in deps or []:
        dep = exact_fields(dep, set(), {"uri", "digest", "name", "downloadLocation", "mediaType", "annotations", "content"}, what="resource descriptor")
        dg = dep.get("digest")
        if not isinstance(dg, Mapping) or not any(k in dg for k in ("sha256", "sha512", "gitCommit")):
            raise fail("ATTESTATION_MATERIALS", "material lacks an approved digest", uri=str(dep.get("uri"))[:256])
        uri = _normalize_uri(str(dep.get("uri", "")))
        if uri in uris:
            raise fail("ATTESTATION_MATERIALS", "duplicate material after URI normalisation", uri=uri[:256])
        uris.add(uri)
    md = rd.get("metadata") or {}
    if policy.max_age_s is not None:
        fin = md.get("finishedOn") if isinstance(md, Mapping) else None
        ts = _rfc3339(fin) if isinstance(fin, str) else None
        if ts is None or now - ts > policy.max_age_s or ts > now + 300:
            raise fail("ATTESTATION_INVALID", "attestation freshness (finishedOn) outside policy")


def _normalize_uri(uri: str) -> str:
    from urllib.parse import urlsplit, urlunsplit
    s = urlsplit(uri.strip())
    host = (s.hostname or "").lower().rstrip(".")
    port = f":{s.port}" if s.port and not ((s.scheme == "https" and s.port == 443) or (s.scheme == "http" and s.port == 80)) else ""
    path = s.path.rstrip("/") if s.path not in ("", "/") else ""
    if path.endswith(".git"):
        path = path[:-4]
    return urlunsplit((s.scheme.lower(), host + port, path, s.query, ""))


def _rfc3339(text: str) -> int | None:
    import datetime
    try:
        return int(datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def check_no_conflicts(atts: Sequence[VerifiedAttestation]) -> None:
    """Multiple SLSA provenance statements for one subject must agree on builder+buildType+params."""
    seen: dict[tuple[str, str], tuple[Any, Any, Any]] = {}
    for a in atts:
        if a.predicate_type != SLSA_V1:
            continue
        key_facts = (_get(a.predicate, "runDetails", "builder", "id"), _get(a.predicate, "buildDefinition", "buildType"),
                     _get(a.predicate, "buildDefinition", "externalParameters"))
        for d in a.subjects.values():
            prev = seen.get((a.predicate_type, d))
            if prev is not None and prev != key_facts:
                raise fail("ATTESTATION_CONFLICT", "contradictory provenance for the same subject", digest=d)
            seen[(a.predicate_type, d)] = key_facts
