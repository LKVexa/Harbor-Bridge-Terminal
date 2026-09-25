"""CycloneDX 1.5 JSON SBOM (MC-032).  Components: this package, vendored pk_core (per-file hashes),
and the interpreter requirement.  Written to evidence/SBOM.cdx.json."""
from __future__ import annotations

import hashlib
import sys
import uuid

from ._common import EVIDENCE, ROOT, read_json, write_json


def build() -> dict:
    version = (ROOT / "VERSION").read_text().strip()
    prov = read_json(ROOT / "_vendor" / "PK_CORE_PROVENANCE.json")
    src_hash = hashlib.sha256()
    for p in sorted(ROOT.glob("*.py")):
        src_hash.update(p.name.encode() + b"\0" + p.read_bytes())
    pk_hash = hashlib.sha256("".join(f"{k}:{v}" for k, v in sorted(prov["files_sha256"].items())).encode()).hexdigest()
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5",
        "serialNumber": "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"inv28/{version}/{src_hash.hexdigest()}")),
        "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv28-unikernel-implementations", "version": version,
                                   "bom-ref": "inv28",
                                   "hashes": [{"alg": "SHA-256", "content": src_hash.hexdigest()}],
                                   "licenses": [{"license": {"name": "All rights reserved (licence pending D-004)"}}]},
                     "tools": [{"name": "tools/sbom.py"}]},
        "components": [
            {"type": "library", "name": "pk_core", "version": "PK_Master_Applied_All_Batches/UC270", "bom-ref": "pk_core",
             "scope": "required", "hashes": [{"alg": "SHA-256", "content": pk_hash}],
             "properties": [{"name": "vendored", "value": "true"},
                            {"name": "source", "value": prov["source"]},
                            {"name": "source_zip_sha256", "value": prov["source_zip_sha256"]}]},
            {"type": "platform", "name": "cpython", "version": ">=3.10", "bom-ref": "cpython", "scope": "required"},
        ],
        "dependencies": [{"ref": "inv28", "dependsOn": ["pk_core", "cpython"]}, {"ref": "pk_core", "dependsOn": ["cpython"]}],
    }


def main(argv=None) -> int:
    write_json(EVIDENCE / "SBOM.cdx.json", build())
    print("SBOM written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
