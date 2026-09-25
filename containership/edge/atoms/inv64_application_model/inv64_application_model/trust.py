"""Artifact trust-policy verification before consumption (MC-15; C045).

Every protected artifact (schema bundle, authz policy, overlay bundle, release
wheel, adjacent-component contract) is verified before it is used::

    verify_artifact(data, artifact_class="policy", version="2026.09.1",
                    envelope=<DSSE in-toto statement>, policy=TrustPolicy(...))

Order (fail-closed at the first failure, each a stable code):

1. class known to the policy, else ``artifact.signature``;
2. signer key IDs and algorithms come from the **policy**, never the envelope;
   signer revoked / past ``not_after`` -> ``artifact.revoked``;
3. at least one valid signature from an allowed signer -> else ``artifact.signature``;
4. statement subject digest equals SHA-256 of the actual bytes -> ``artifact.digest``;
5. builder ID and source repository/ref in the class allowlist -> ``artifact.provenance``;
6. digest not on the deny list (revoked release) -> ``artifact.revoked``;
7. version in the allow list (if any), at or above the class floor, and not
   below the highest version previously accepted by this verifier
   (anti-downgrade / substitution of an older valid artifact) -> ``artifact.version``.

The trust policy itself is versioned; :class:`TrustStore` activates a new
policy only if it is signed by a *root* key held out-of-band, keeps the prior
policy for rollback, and records ``policy.version`` + tool version in every result.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Mapping

from .errors import Inv64Error
from .provenance import PAYLOAD_TYPE, check_signature, pae

VERIFIER_VERSION = "inv64-trust/1.0"


def _vtuple(v: str) -> tuple:
    out = []
    for part in str(v).replace("-", ".").split("."):
        out.append((0, int(part)) if part.isdigit() else (1, part))
    return tuple(out)


@dataclass
class TrustPolicy:
    version: str
    signers: Mapping[str, dict]   # kid -> {"alg", "key" (bytes), "not_after" (epoch|None), "revoked" (bool)}
    classes: Mapping[str, dict]   # class -> {"signers": [...], "builders": [...], "sources": [...],
                                  #           "min_version": str, "allowed_versions": [...]|None}
    denied_digests: frozenset = frozenset()
    grace_s: float = 0.0          # grace for signer not_after when trusted time is uncertain


@dataclass
class TrustStore:
    root_keys: Mapping[str, tuple[str, bytes]]    # kid -> (alg, key); provisioned out-of-band
    active: TrustPolicy | None = None
    previous: TrustPolicy | None = None
    floors: dict = field(default_factory=dict)    # class -> highest accepted version
    audit: object = None                          # AuditLog; trust changes are audited fail-closed

    def activate(self, policy: TrustPolicy, envelope: dict, policy_bytes: bytes, *, actor: str = "inv64") -> None:
        """Activate a policy only if ``policy_bytes`` is signed by a root key."""
        try:
            st = _open_envelope(envelope, {k: v for k, v in self.root_keys.items()})
            digest = hashlib.sha256(policy_bytes).hexdigest()
            if not any(s.get("digest", {}).get("sha256") == digest for s in st.get("subject", [])):
                raise Inv64Error("artifact.digest", details={"artifact": "trust-policy"})
        except Inv64Error as exc:
            if self.audit is not None:
                self.audit.append("trust.activate", actor=actor, outcome="rejected", reason=exc.code)
            raise
        if self.audit is not None:
            self.audit.append("trust.activate", actor=actor, outcome="active", resource=policy.version,
                              fail_closed=True, digest=digest)
        self.previous, self.active = self.active, policy

    def rollback(self, *, actor: str = "inv64") -> None:
        if self.previous is None:
            raise Inv64Error("activation.no_known_good")
        if self.audit is not None:
            self.audit.append("trust.rollback", actor=actor, outcome="active", resource=self.previous.version,
                              fail_closed=True)
        self.active, self.previous = self.previous, self.active


def _open_envelope(envelope: dict, keys: Mapping[str, tuple[str, bytes]]) -> dict:
    if not isinstance(envelope, dict) or envelope.get("payloadType") != PAYLOAD_TYPE:
        raise Inv64Error("artifact.signature", details={"reason": "not a DSSE in-toto envelope"})
    try:
        payload = base64.b64decode(envelope["payload"], validate=True)
    except (KeyError, ValueError, TypeError):
        raise Inv64Error("artifact.signature", details={"reason": "payload"})
    msg = pae(PAYLOAD_TYPE, payload)
    ok = False
    for s in envelope.get("signatures", []) if isinstance(envelope.get("signatures"), list) else []:
        entry = keys.get(s.get("keyid")) if isinstance(s, dict) else None
        if entry is None:
            continue
        try:
            sig = base64.b64decode(s.get("sig", ""), validate=True)
        except ValueError:
            continue
        if check_signature(entry[0], entry[1], msg, sig):
            ok = True
            break
    if not ok:
        raise Inv64Error("artifact.signature", details={"reason": "no valid signature from a trusted key"})
    try:
        return json.loads(payload)
    except ValueError:
        raise Inv64Error("artifact.signature", details={"reason": "payload not JSON"})


def verify_artifact(data: bytes, *, artifact_class: str, version: str, envelope: dict,
                    store: TrustStore, name: str | None = None, now: float | None = None,
                    record_floor: bool = True) -> dict:
    pol = store.active
    if pol is None:
        raise Inv64Error("artifact.signature", details={"reason": "no active trust policy"})
    cls = pol.classes.get(artifact_class)
    if cls is None:
        raise Inv64Error("artifact.signature", details={"reason": "unknown artifact class"})
    now = time.time() if now is None else now
    keys = {}
    for kid in cls["signers"]:
        s = pol.signers.get(kid)
        if s is None:
            continue
        if s.get("revoked") or (s.get("not_after") is not None and now > s["not_after"] + pol.grace_s):
            # a revoked/expired signer is excluded; if it was the only signature, fail as revoked
            sigs = [x.get("keyid") for x in envelope.get("signatures", []) if isinstance(x, dict)] \
                if isinstance(envelope, dict) else []
            if kid in sigs and len(sigs) == 1:
                raise Inv64Error("artifact.revoked", details={"signer": kid})
            continue
        keys[kid] = (s["alg"], s["key"])
    stmt = _open_envelope(envelope, keys)
    digest = hashlib.sha256(data).hexdigest()
    subj = [x for x in stmt.get("subject", []) if isinstance(x, dict)]
    if not any(x.get("digest", {}).get("sha256") == digest and (name is None or x.get("name") == name) for x in subj):
        raise Inv64Error("artifact.digest", details={"actual": digest})
    pred = stmt.get("predicate", {}) if isinstance(stmt.get("predicate"), dict) else {}
    builder = pred.get("runDetails", {}).get("builder", {}).get("id")
    params = pred.get("buildDefinition", {}).get("externalParameters", {})
    if cls.get("builders") and builder not in cls["builders"]:
        raise Inv64Error("artifact.provenance", details={"builder": builder})
    if cls.get("sources") and params.get("source") not in cls["sources"]:
        raise Inv64Error("artifact.provenance", details={"source": params.get("source")})
    if params.get("version") not in (None, version):
        raise Inv64Error("artifact.provenance", details={"reason": "statement version differs"})
    if digest in pol.denied_digests:
        raise Inv64Error("artifact.revoked", details={"digest": digest})
    allowed = cls.get("allowed_versions")
    if allowed is not None and version not in allowed:
        raise Inv64Error("artifact.version", details={"version": version})
    if cls.get("min_version") and _vtuple(version) < _vtuple(cls["min_version"]):
        raise Inv64Error("artifact.version", details={"version": version, "floor": cls["min_version"]})
    floor = store.floors.get(artifact_class)
    if floor is not None and _vtuple(version) < _vtuple(floor):
        raise Inv64Error("artifact.version", details={"reason": "downgrade", "version": version, "floor": floor})
    if record_floor:
        store.floors[artifact_class] = version if floor is None or _vtuple(version) > _vtuple(floor) else floor
    return {"schema": "PK_APP_ARTIFACT_VERIFICATION/1", "result": "PASS", "class": artifact_class,
            "version": version, "digest": digest, "builder": builder, "policy_version": pol.version,
            "verifier": VERIFIER_VERSION}
