"""Approved-version manifest and artifact verification (C031, C032, C045, INV71-X004).

A manifest names each production artifact class by exact version and SHA-256
digest, with compatibility edges and a monotonically increasing manifest
serial (so an old-but-validly-signed manifest cannot be replayed).  Floating
tags (``latest``, ``stable``, ranges) are rejected.  Verification is fail
closed: missing file, digest mismatch, bad signature, unapproved version,
revoked digest, stale serial, or unpinned entry all refuse the load.

The signature here is HMAC-SHA256 as a reference for the verification flow.
Production must use asymmetric signatures (e.g. Sigstore/cosign or an HSM-held
key) - see docs/SUPPLY_CHAIN.md.  The shipped ``artifacts/approved-manifest.json``
is deliberately UNPINNED: this repository holds no Firecracker, kernel or rootfs
bytes, so any digest written here would be invented.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .config import canonical_bytes
from .errors import ControlError

ARTIFACT_CLASSES = ("node_agent", "firecracker", "jailer", "guest_kernel", "guest_rootfs",
                    "snapshot", "seccomp_profile", "policy_bundle")
_FLOATING = re.compile(r"(latest|stable|edge|main|master|\*|\^|~|>|<|x$)", re.I)
_SEMVER = re.compile(r"^v?\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")
UNPINNED = "UNPINNED"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Verified:
    cls: str
    version: str
    digest: str


class ManifestVerifier:
    def __init__(self, key: bytes, *, min_serial: int = 0) -> None:
        self._key = key
        self.min_serial = min_serial
        self.revoked: set[str] = set()

    def sign(self, manifest: Mapping[str, Any]) -> str:
        body = {k: v for k, v in manifest.items() if k != "signature"}
        return hmac.new(self._key, canonical_bytes(body), hashlib.sha256).hexdigest()

    def check_manifest(self, manifest: Mapping[str, Any]) -> list[str]:
        """Return a list of problems; empty means the manifest is usable."""
        problems: list[str] = []
        if manifest.get("schema") != "PK_HEAVYBOX_ARTIFACT_MANIFEST/1":
            problems.append("schema")
        sig = manifest.get("signature", "")
        if not isinstance(sig, str) or not hmac.compare_digest(sig, self.sign(manifest)):
            problems.append("signature")
        serial = manifest.get("serial")
        if not isinstance(serial, int) or serial < self.min_serial:
            problems.append("stale_serial")
        arts = manifest.get("artifacts", {})
        for c in ARTIFACT_CLASSES:
            a = arts.get(c)
            if not isinstance(a, dict):
                problems.append(f"{c}:missing")
                continue
            v, d = str(a.get("version", "")), str(a.get("sha256", ""))
            if v == UNPINNED or d == UNPINNED:
                problems.append(f"{c}:unpinned")
                continue
            if _FLOATING.search(v) or not _SEMVER.match(v):
                problems.append(f"{c}:floating_or_invalid_version")
            if not re.fullmatch(r"[0-9a-f]{64}", d):
                problems.append(f"{c}:invalid_digest")
            if d in self.revoked:
                problems.append(f"{c}:revoked")
        return problems

    def verify_artifact(self, manifest: Mapping[str, Any], cls: str, path: Path) -> Verified:
        problems = self.check_manifest(manifest)
        if "signature" in problems:
            raise ControlError("ARTIFACT.SIGNATURE_INVALID")
        if "stale_serial" in problems or any(p.startswith(cls + ":") for p in problems):
            if f"{cls}:revoked" in problems:
                raise ControlError("ARTIFACT.REVOKED", cls)
            raise ControlError("ARTIFACT.UNAPPROVED_VERSION", cls)
        entry = manifest["artifacts"][cls]
        if not path.is_file():
            raise ControlError("ARTIFACT.DIGEST_MISMATCH", f"{cls}: missing file")
        actual = sha256_file(path)
        if not hmac.compare_digest(actual, entry["sha256"]):
            raise ControlError("ARTIFACT.DIGEST_MISMATCH", cls)
        return Verified(cls, entry["version"], actual)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
