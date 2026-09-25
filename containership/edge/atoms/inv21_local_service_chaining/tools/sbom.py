"""CycloneDX 1.5 SBOM + unsigned provenance statement for a built artifact (GAP-017)."""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import time
import uuid


def sha256(p) -> str:
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def sbom(artifact: str, version: str, files: dict) -> dict:
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
        "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "component": {"type": "library", "name": "inv21-local-service-chaining", "version": version,
                                   "hashes": [{"alg": "SHA-256", "content": sha256(artifact)}],
                                   "licenses": [{"license": {"name": "LicenseRef-INV21-Pending"}}]}},
        "components": [
            {"type": "platform", "name": "cpython", "version": ">=3.10,<3.14", "description": "runtime; stdlib only"},
        ] + [{"type": "file", "name": n, "hashes": [{"alg": "SHA-256", "content": h}]} for n, h in sorted(files.items())],
        "dependencies": [{"ref": "inv21-local-service-chaining", "dependsOn": []}],
        "properties": [{"name": "inv21:third_party_runtime_dependencies", "value": "0"},
                       {"name": "inv21:pk_core", "value": "UNRESOLVED (conformance adapter only)"}],
    }


def provenance(artifacts: dict, source_digest: str, builder: str) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": n, "digest": {"sha256": h}} for n, h in artifacts.items()],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv21/pep517-setuptools", "externalParameters":
                                              {"source_tree_sha256": source_digest, "SOURCE_DATE_EPOCH": "1790000000"}},
                          "runDetails": {"builder": {"id": builder}, "metadata": {"python": platform.python_version()}}},
            "signature": None, "signature_status": "UNSIGNED - no signing identity available (GAP-017)"}
