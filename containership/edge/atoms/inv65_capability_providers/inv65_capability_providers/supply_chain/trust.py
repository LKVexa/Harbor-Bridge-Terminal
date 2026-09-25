"""Provider artifact trust and implementation pinning (M20).

``provider_catalog.json`` pins, per contract, the allowed implementation
name/version/sha256.  Registration and host start-up call ``require`` -- an
unlisted digest is refused (PK_PROVIDER_UNTRUSTED_ARTIFACT).  ``sbom()`` emits a
CycloneDX-1.5-shaped SBOM of this package's own files with digests;
``provenance()`` emits an in-toto-shaped statement over the same digests.
Signing of those documents belongs to the release pipeline (M29) and is NOT
performed here.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

from ..errors.mapping import ProviderFault

PKG = pathlib.Path(__file__).resolve().parents[1]
_SKIP_DIRS = {"__pycache__", ".git", "evidence", "sbom", "provenance", "release"}


def file_digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def package_files() -> list[pathlib.Path]:
    return sorted(p for p in PKG.rglob("*") if p.is_file() and not (set(p.relative_to(PKG).parts[:-1]) & _SKIP_DIRS)
                  and p.suffix != ".pyc")


class ArtifactTrust:
    def __init__(self, catalog: dict):
        self.catalog = catalog

    @classmethod
    def load(cls, path: str | pathlib.Path) -> "ArtifactTrust":
        return cls(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))

    def require(self, contract_id: str, digest: str) -> dict:
        for impl in self.catalog.get("contracts", {}).get(contract_id, []):
            if impl.get("sha256") == digest and not impl.get("revoked", False):
                return impl
        raise ProviderFault("PK_PROVIDER_UNTRUSTED_ARTIFACT", "implementation digest not allowlisted for contract")


def sbom(version: str) -> dict:
    comps = [{"type": "file", "name": str(p.relative_to(PKG)), "hashes": [{"alg": "SHA-256", "content": file_digest(p)}]}
             for p in package_files()]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv65-capability-providers", "version": version},
                         "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            "components": comps,
            "dependencies": [{"ref": "pk_core", "note": "external, unpinned: see docs/dependencies/pk_core.md"},
                             {"ref": "cryptography", "note": "optional extra [crypto]"}]}


def provenance(version: str, sbom_doc: dict) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": c["name"], "digest": {"sha256": c["hashes"][0]["content"]}} for c in sbom_doc["components"]],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv65/tools/release.py", "externalParameters": {"version": version}},
                          "runDetails": {"builder": {"id": "UNSIGNED-local-build"}, "metadata": {"note": "unsigned; release signing is an owner-held step"}}}}
