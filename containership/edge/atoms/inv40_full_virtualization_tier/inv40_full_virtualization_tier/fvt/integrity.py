"""Artifact integrity: digest, signature and approved-version verification
(INV-40-C045, REPO-006 support).

Guest images and policy bundles are admitted only when (1) their sha256 digest
matches the requested digest, (2) the digest is on the active config's
approved list, and (3) a detached signature verifies.  The signature scheme
here is HMAC-SHA256 over the digest with a key from the KeyProvider; an
asymmetric (Ed25519/sigstore) verifier is the production requirement and is
recorded as blocker SEC-SIGN because the stdlib has no Ed25519.
"""
from __future__ import annotations

import hashlib
import hmac
import pathlib

from .errors import OpError


def file_digest(path: str | pathlib.Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def sign_digest(key: bytes, dig: str) -> str:
    return hmac.new(key, dig.encode(), hashlib.sha256).hexdigest()


def verify_artifact(path, *, expected: str, approved: list[str], signature: str | None, key: bytes | None) -> str:
    actual = file_digest(path)
    if actual != expected:
        raise OpError("PK_FULL_VM_INTEGRITY_FAILED", "digest mismatch", expected=expected, actual=actual)
    if expected not in approved:
        raise OpError("PK_FULL_VM_INTEGRITY_FAILED", "digest not on approved list", digest=expected)
    if not signature or key is None:
        raise OpError("PK_FULL_VM_INTEGRITY_FAILED", "unsigned artifact", digest=expected)
    if not hmac.compare_digest(sign_digest(key, expected), signature):
        raise OpError("PK_FULL_VM_INTEGRITY_FAILED", "bad signature", digest=expected)
    return actual


def manifest(root: pathlib.Path, exclude=("MANIFEST.sha256",)) -> list[tuple[str, str]]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and rel not in exclude and "__pycache__" not in rel and not rel.startswith(("evidence/", ".")):
            out.append((hashlib.sha256(p.read_bytes()).hexdigest(), rel))
    return out
