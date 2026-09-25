"""Generate COMPATIBILITY.json - machine-readable compatibility matrix (#28)."""
import json
import os
import sys

import _path

from gap07_artifact_provenance_signing import __version__, algorithms
from gap07_artifact_provenance_signing.errors import ERROR_CODES
from gap07_artifact_provenance_signing.registry import INDEX_TYPES, MANIFEST_TYPES
from gap07_artifact_provenance_signing.signing import KINDS

DOC = {
    "schema": "PK_COMPATIBILITY/1", "component": "GAP-07", "version": __version__,
    "envelopes": {
        "PK_SIGNATURE/1": {"verify": "rejected", "since": "5.0.0"},
        "PK_SIGNATURE/2": {"verify": "reference-migration-only (signing.verify_legacy_v2_reference, audited, never production)", "sign": "reference TrustStore only", "sunset": "7.0.0"},
        "PK_SIGNATURE/3": {"verify": "production", "sign": "production"},
        "PK_PROVENANCE/2": {"verify": "supported (local chain)"},
        "DSSE v1 / in-toto Statement v1": {"verify": "production"},
        "SLSA Provenance v1": {"verify": "production (predicate validated)"},
        "SLSA Provenance v0.2": {"verify": "rejected unless policy explicitly adds predicate type (no validator)"},
        "CycloneDX": {"versions": ["1.4", "1.5", "1.6"]}, "SPDX": {"versions": ["SPDX-2.3"]},
        "PK_CERT/1": {"verify": "production"}, "X.509 code-signing": {"verify": "production (EKU codeSigning, one URI SAN)"},
        "PK_CHECKPOINT/1": {"verify": "production"}, "PK_TRUST_GENERATION/1": {}, "PK_TRUST_DELTA/1": {}, "PK_POLICY_BUNDLE/1": {"adapter_version": 1},
        "PK_TIME_ATTESTATION/1": {}, "PK_ARTIFACT_BUNDLE/1": {}, "PK_ADMISSION_DECISION/1": {},
    },
    "algorithms": algorithms.registry_document()["algorithms"],
    "artifact_kinds": sorted(KINDS),
    "oci_media_types": sorted(MANIFEST_TYPES | INDEX_TYPES),
    "wasm": {"core_module": "version 1 layer 0", "component": "layer 1"},
    "runtimes": {"python": [">=3.10"], "cryptography": ">=45,<48", "os": ["linux", "windows", "macos"], "architectures": ["x86_64", "aarch64"]},
    "kms_providers": ["aws-kms", "azure-kv", "gcp-kms", "vault-transit", "pkcs11", "software (dev only)"],
    "error_codes": {k: {"class": v[0], "transient": v[1]} for k, v in ERROR_CODES.items()},
    "migration": {"5.0.0->6.0.0": "Re-sign artifacts under PK_SIGNATURE/3 using migration tooling; v2 signatures are verifiable only via the audited reference migration verifier and never satisfy production policy. TrustStore(v5) remains importable as reference API."},
}

if __name__ == "__main__":
    with open(os.path.join(_path.ROOT, "COMPATIBILITY.json"), "w") as fh:
        json.dump(DOC, fh, indent=2)
        fh.write("\n")
    print("ok")
