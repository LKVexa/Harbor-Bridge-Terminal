"""Artifact / policy integrity verification (MC-012, INV-58-C045).

A consumed executable or policy artifact is trusted only if **all** hold:

1. It is described by a ``PK_MESH_ARTIFACT/1`` manifest with name, version,
   SHA-256 digest, builder, source repository/revision and build time.
2. The manifest carries a valid signature from an approved signer key
   (HMAC-SHA256 under a key resolved through a secret reference; replace with
   an asymmetric/Sigstore verifier via :class:`Verifier` ``signature_check`` —
   see ``docs/RESIDUAL_RISKS.md`` RR-03).
3. The artifact bytes hash to the manifest digest.
4. ``(name, version)`` is on the approved-version list and not revoked.

Any failure raises ``MeshError('E_INTEGRITY')`` — there is no warn-only mode.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Callable, Mapping

from .errors import MeshError

MANIFEST_SCHEMA = "PK_MESH_ARTIFACT/1"
REQUIRED = ("schema", "name", "version", "digest", "builder", "source_repo", "source_rev", "built_at")


def _canon(d: Mapping) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sign_manifest(manifest: Mapping, key: bytes) -> str:
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return "hmac-sha256:" + hmac.new(key, _canon(body), hashlib.sha256).hexdigest()


def hmac_check(key_provider: Callable[[], bytes]):
    def check(manifest: Mapping) -> bool:
        sig = manifest.get("signature")
        if not isinstance(sig, str):
            return False
        return hmac.compare_digest(sig, sign_manifest(manifest, key_provider()))
    return check


@dataclass
class Verifier:
    signature_check: Callable[[Mapping], bool]
    approved: Mapping[str, frozenset] = field(default_factory=dict)  # name -> versions
    revoked: frozenset = frozenset()  # digests

    def verify(self, manifest: Mapping, data: bytes) -> dict:
        def fail(reason):
            raise MeshError("E_INTEGRITY", reason, {"artifact": str(manifest.get("name", "?"))[:64]})
        if not isinstance(manifest, Mapping):
            fail("manifest must be an object")
        missing = [k for k in REQUIRED if not manifest.get(k)]
        if missing:
            fail(f"manifest missing provenance fields {missing}")
        if manifest["schema"] != MANIFEST_SCHEMA:
            fail("unsupported manifest schema")
        try:
            ok = bool(self.signature_check(manifest))
        except Exception:
            ok = False  # signer/key service unavailable -> fail closed
        if not ok:
            fail("signature invalid or signer unavailable")
        actual = sha256_bytes(data)
        if not hmac.compare_digest(actual, str(manifest["digest"])):
            fail("digest mismatch")
        if actual in self.revoked:
            fail("artifact digest revoked")
        if manifest["version"] not in self.approved.get(manifest["name"], frozenset()):
            fail("artifact version not approved")
        return {"name": manifest["name"], "version": manifest["version"], "digest": actual, "verified": True}
