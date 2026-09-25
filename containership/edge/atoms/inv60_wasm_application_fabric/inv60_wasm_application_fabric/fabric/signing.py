"""M35 - artifact signature and provenance verification (in-toto/SLSA-shaped).

An artifact envelope carries an in-toto style statement::

  {"_type": "https://in-toto.io/Statement/v1",
   "subject": [{"name": ..., "digest": {"sha256": hex}}],
   "predicateType": "https://slsa.dev/provenance/v1",
   "predicate": {"builder": {"id": ...}, "buildLevel": int,
                 "source": {"uri": ..., "commit": ...}, "materials": [...]}}

signed (Ed25519) by a signer key. ``TrustPolicy.verify`` checks, fail closed:
algorithm allowed, signer trusted and not revoked, signer allowed for subject,
signature valid, statement subject digest == sha256(bytes), provenance level >=
policy minimum, builder allowed, trust-root version not stale. It returns a
``VerifiedArtifact`` holding the exact verified bytes (no TOCTOU re-read).
"""
from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import time
from dataclasses import dataclass, field

from . import ed25519
from .errors import FabricError

ALLOWED_ALGORITHMS = ("ed25519",)
DIGEST_ALGORITHMS = ("sha256",)


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def statement_for(name: str, data: bytes, *, builder: str, level: int, source_uri: str,
                  commit: str, materials=()) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": name, "digest": {"sha256": hashlib.sha256(data).hexdigest()}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"builder": {"id": builder}, "buildLevel": int(level),
                          "source": {"uri": source_uri, "commit": commit},
                          "materials": list(materials)}}


def sign_statement(statement: dict, signer_id: str, seed: bytes) -> dict:
    payload = canonical(statement)
    return {"payloadType": "application/vnd.in-toto+json",
            "payload": base64.b64encode(payload).decode(),
            "signatures": [{"keyid": signer_id, "alg": "ed25519",
                            "sig": base64.b64encode(ed25519.sign(seed, payload)).decode()}]}


@dataclass
class VerifiedArtifact:
    ref: str
    data: bytes
    signer: str
    builder: str
    level: int
    policy_version: str
    source: dict

    def record(self) -> dict:
        return {"ref": self.ref, "signer": self.signer, "builder": self.builder,
                "slsa_level": self.level, "policy_version": self.policy_version, "source": self.source}


@dataclass
class TrustPolicy:
    version: str = "inv60-trust/1.0.0"
    signers: dict = field(default_factory=dict)       # keyid -> {"public_key": bytes, "subjects": [glob]}
    revoked_signers: set = field(default_factory=set)
    allowed_builders: tuple = ()
    min_level: int = 2
    trust_root_version: int = 1
    trust_root_issued_at: float = field(default_factory=time.time)
    max_root_age_s: float = 30 * 86400
    clock: object = time.time

    def add_signer(self, keyid: str, public_key: bytes, subjects=("*",)) -> None:
        self.signers[keyid] = {"public_key": bytes(public_key), "subjects": list(subjects)}

    def verify(self, name: str, data: bytes, envelope: dict) -> VerifiedArtifact:
        data = bytes(data)
        if self.clock() - self.trust_root_issued_at > self.max_root_age_s:
            raise FabricError("SIGNATURE_INVALID", "trusted root is stale; refresh before admitting (offline rule)")
        try:
            payload = base64.b64decode(envelope["payload"], validate=True)
            sigs = envelope["signatures"]
            statement = json.loads(payload)
        except Exception:
            raise FabricError("SIGNATURE_INVALID", "malformed envelope") from None
        if envelope.get("payloadType") != "application/vnd.in-toto+json":
            raise FabricError("SIGNATURE_INVALID", "unexpected payload type")
        good = None
        for s in sigs if isinstance(sigs, list) else []:
            if s.get("alg") not in ALLOWED_ALGORITHMS:
                continue
            kid = s.get("keyid")
            if kid in self.revoked_signers or kid not in self.signers:
                continue
            try:
                raw = base64.b64decode(s.get("sig", ""), validate=True)
            except Exception:
                continue
            if ed25519.verify(self.signers[kid]["public_key"], payload, raw):
                good = kid
                break
        if good is None:
            raise FabricError("SIGNATURE_INVALID", "no valid signature from a trusted, unrevoked signer")
        if not any(fnmatch.fnmatchcase(name, g) for g in self.signers[good]["subjects"]):
            raise FabricError("SIGNATURE_INVALID", f"signer {good} not authorised for subject {name!r}")
        subjects = statement.get("subject") or []
        want = hashlib.sha256(data).hexdigest()
        if not any(sub.get("name") == name and sub.get("digest", {}).get("sha256") == want for sub in subjects):
            raise FabricError("SIGNATURE_INVALID", "statement subject does not match artifact bytes")
        pred = statement.get("predicate") or {}
        level = int(pred.get("buildLevel", 0))
        builder = (pred.get("builder") or {}).get("id", "")
        if level < self.min_level:
            raise FabricError("SIGNATURE_INVALID", f"provenance level {level} below minimum {self.min_level}")
        if self.allowed_builders and builder not in self.allowed_builders:
            raise FabricError("SIGNATURE_INVALID", f"builder {builder!r} not allowed")
        return VerifiedArtifact("sha256:" + want, data, good, builder, level, self.version,
                                dict(pred.get("source") or {}))
