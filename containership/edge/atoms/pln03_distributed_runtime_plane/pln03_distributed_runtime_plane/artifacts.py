"""Artifact digest allowlist and provenance verification (MC-030).

Verifies (1) the artifact's SHA-256 is on a pinned allowlist, and (2) an in-toto /
SLSA-style provenance statement names that digest, an allowed builder and source
repository, and (optionally) carries an HMAC seal from a trusted provenance key.
Public-key signature verification (Sigstore/cosign) is an external dependency
recorded in DEPENDENCIES.lock.json and is not re-implemented here.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from .runtime import RuntimePlaneError


class ArtifactRejected(RuntimePlaneError):
    code = "PK_CAPABILITY_DENIED"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def verify_artifact(data: bytes, *, allowlist: set[str], provenance: dict | None,
                    allowed_builders: set[str], allowed_sources: set[str],
                    provenance_key: bytes | None = None) -> str:
    d = "sha256:" + hashlib.sha256(data).hexdigest()
    if d not in allowlist:
        raise ArtifactRejected("artifact digest not on allowlist", digest=d)
    if provenance is None:
        raise ArtifactRejected("provenance statement required", digest=d)
    subjects = {f"sha256:{s.get('digest', {}).get('sha256', '')}" for s in provenance.get("subject", [])}
    if d not in subjects:
        raise ArtifactRejected("provenance does not name this artifact", digest=d)
    pred = provenance.get("predicate", {})
    if pred.get("builder", {}).get("id") not in allowed_builders:
        raise ArtifactRejected("untrusted builder")
    if pred.get("source") not in allowed_sources:
        raise ArtifactRejected("untrusted source repository")
    if provenance_key is not None:
        body = {k: v for k, v in provenance.items() if k != "seal"}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        if not hmac.compare_digest(hmac.new(provenance_key, raw, hashlib.sha256).hexdigest(),
                                   str(provenance.get("seal", ""))):
            raise ArtifactRejected("provenance seal invalid")
    return d
