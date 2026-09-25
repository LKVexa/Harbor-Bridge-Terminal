"""GAP02-MC-20 — Package/artifact provenance enforcement.

Before a probe plugin module is loaded, its file digest must match an approved
manifest entry, its version must be in the approved set, the manifest must
itself verify against a trusted signer, and its declared dependencies must
satisfy the dependency policy. Loads happen from the verified bytes (no TOCTOU
re-read).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from typing import Any

from .errors import Code, Gap02Error


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class ProvenancePolicy:
    def __init__(self, manifest: dict, *, verifier, allowed_licenses=frozenset({"MIT", "Apache-2.0", "BSD-3-Clause"}),
                 forbidden_deps=frozenset()):
        body = json.dumps(manifest.get("plugins"), sort_keys=True, separators=(",", ":")).encode()
        import base64
        try:
            sig = base64.b64decode(manifest.get("signature", ""), validate=True)
        except ValueError as e:
            raise Gap02Error(Code.PROVENANCE_FAILURE, "manifest signature encoding") from e
        if not verifier.verify(manifest.get("key_id", ""), manifest.get("alg", ""), body, sig):
            raise Gap02Error(Code.PROVENANCE_FAILURE, "manifest signature invalid")
        self.plugins: dict[str, Any] = manifest["plugins"]
        self.allowed_licenses, self.forbidden = allowed_licenses, forbidden_deps

    def load(self, name: str, path: str) -> types.ModuleType:
        entry = self.plugins.get(name)
        if not entry:
            raise Gap02Error(Code.PROVENANCE_FAILURE, f"plugin {name} not approved")
        with open(path, "rb") as f:
            data = f.read(4_000_000)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise Gap02Error(Code.PROVENANCE_FAILURE, f"{name}: digest mismatch")
        if entry.get("version") not in entry.get("approved_versions", [entry.get("version")]):
            raise Gap02Error(Code.PROVENANCE_FAILURE, f"{name}: version not approved")
        if entry.get("license") not in self.allowed_licenses:
            raise Gap02Error(Code.PROVENANCE_FAILURE, f"{name}: license {entry.get('license')}")
        bad = set(entry.get("dependencies", [])) & set(self.forbidden)
        if bad:
            raise Gap02Error(Code.PROVENANCE_FAILURE, f"{name}: forbidden deps {sorted(bad)}")
        if not entry.get("provenance", {}).get("builder"):
            raise Gap02Error(Code.PROVENANCE_FAILURE, f"{name}: no provenance attestation")
        mod = types.ModuleType(f"gap02_plugin_{name}")
        mod.__file__ = path
        exec(compile(data, path, "exec"), mod.__dict__)  # verified bytes only
        return mod
