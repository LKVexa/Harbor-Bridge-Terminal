"""Emit a CycloneDX 1.5 JSON SBOM (stdlib; no network).  Usage: sbom.py OUT [--wheel W]"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, sha256_file, source_identity, version  # noqa: E402


def build(wheel=None) -> dict:
    vend = json.loads((ROOT / "vendor" / "VENDORED.json").read_text())
    comp = {
        "type": "library",
        "bom-ref": "inv23",
        "name": "inv23-hardware-virtualization-primitive",
        "version": version(),
        "supplier": {"name": "David Paul Russell", "contact": [{"email": "davidpaulrussell@linearfinance.org"}]},
        "licenses": [{"license": {"name": "UNDETERMINED (see LICENSE-STATUS.md)"}}],
        "hashes": [{"alg": "SHA-256", "content": source_identity()["tree_sha256"]}],
    }
    if wheel:
        comp["hashes"].append({"alg": "SHA-256", "content": sha256_file(wheel)})
    components = [
        {
            "type": "library",
            "bom-ref": "pk_core",
            "name": "pk_core",
            "version": vend["version"],
            "scope": "optional",
            "description": "Vendored conformance runtime (test/conformance only); " + vend["source"],
            "supplier": {"name": "David Paul Russell"},
            "licenses": [{"license": {"name": "UNDETERMINED (owner's own material)"}}],
            "hashes": [{"alg": "SHA-256", "content": vend["tree_sha256"]}],
            "pedigree": {"notes": "unmodified copy; per-file SHA-256 pins in vendor/VENDORED.json"},
        },
        {
            "type": "platform",
            "bom-ref": "cpython",
            "name": "CPython",
            "version": ">=3.9",
            "scope": "required",
            "description": "Runtime uses only the standard library; no native helper is shipped.",
        },
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "component": comp,
            "tools": {"components": [{"type": "application", "name": "inv23 tools/sbom.py"}]},
        },
        "components": components,
        "dependencies": [{"ref": "inv23", "dependsOn": ["cpython"]}, {"ref": "pk_core", "dependsOn": ["cpython"]}],
    }


def validate(doc: dict) -> list:
    errs = []
    for k in ("bomFormat", "specVersion", "serialNumber", "metadata", "components"):
        if k not in doc:
            errs.append(f"missing {k}")
    if doc.get("bomFormat") != "CycloneDX" or doc.get("specVersion") != "1.5":
        errs.append("not CycloneDX 1.5")
    for c in doc.get("components", []):
        if not c.get("name") or not c.get("bom-ref"):
            errs.append("component missing name/bom-ref")
    return errs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--wheel")
    a = ap.parse_args()
    d = build(a.wheel)
    e = validate(d)
    if e:
        sys.exit("invalid SBOM: " + "; ".join(e))
    pathlib.Path(a.out).write_text(json.dumps(d, indent=1) + "\n")
