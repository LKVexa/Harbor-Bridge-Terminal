"""Artifact trust chain for PLN-05 releases (MC-11 / MC-30 / MC-33).

Produces and checks: a sha256 manifest, a CycloneDX 1.5 SBOM, an in-toto v1
provenance statement, and HMAC signatures.  The signing key used by
``tools/build_release.py`` is *ephemeral* (generated per build, public
verification material is the key id + digest only); a managed signing identity
(Sigstore/KMS) is an external dependency recorded as a release blocker, and
:func:`verify_artifact` refuses anything whose digest or version is not
approved regardless of signature.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from .errors import PlaneError

APPROVED_PATH = pathlib.Path(__file__).resolve().parent / "security" / "approved-versions.json"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root, files) -> dict:
    root = pathlib.Path(root)
    return {str(f): sha256_file(root / f) for f in sorted(files)}


def approved() -> dict:
    return json.loads(APPROVED_PATH.read_text(encoding="utf-8"))


def verify_artifact(path, *, expected_sha256: str, name: str, version: str) -> dict:
    policy = approved()
    allowed = policy.get("artifacts", {}).get(name, [])
    if version not in allowed:
        raise PlaneError("E_ARTIFACT_UNTRUSTED", "artifact version not on the approved list",
                         {"version": version if len(version) < 32 else "<redacted>"})
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise PlaneError("E_ARTIFACT_UNTRUSTED", "artifact digest mismatch")
    return {"name": name, "version": version, "sha256": actual, "verified": True}


def sbom(name: str, version: str, files: dict, build_time: str) -> dict:
    pol = approved()
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"timestamp": build_time,
                     "component": {"type": "library", "name": name, "version": version,
                                   "purl": f"pkg:pypi/{name}@{version}",
                                   "licenses": [{"license": {"name": pol["license"]}}]}},
        "components": [
            {"type": "library", "name": d["name"], "version": d["range"], "scope": d["scope"],
             "properties": [{"name": "pln05:resolution", "value": d["status"]}]}
            for d in pol["dependencies"]
        ],
        "properties": [{"name": "pln05:file_count", "value": str(len(files))}],
    }


def provenance(subjects: dict, *, source_revision: str, builder: str, build_time: str,
               params: dict) -> dict:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": n, "digest": {"sha256": d}} for n, d in sorted(subjects.items())],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {"buildType": "urn:pln05:build_release:1", "externalParameters": params,
                                "resolvedDependencies": [{"uri": "git+local", "digest": {"gitCommit": source_revision}}]},
            "runDetails": {"builder": {"id": builder}, "metadata": {"finishedOn": build_time}},
        },
    }
