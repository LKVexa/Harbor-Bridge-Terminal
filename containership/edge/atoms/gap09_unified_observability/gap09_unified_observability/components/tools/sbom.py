"""Packaging/dependency lock/SBOM (54): a CycloneDX-1.5-shaped JSON SBOM
listing every packaged file with its sha256, the declared runtime
dependencies (none beyond CPython stdlib) and the test-lane tools."""
from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDE_DIRS = {"__pycache__", ".git"}
LANES = [
    {"name": "jsonschema", "scope": "optional", "purpose": "test lane: contract-schema conformance (45)"},
    {"name": "node", "scope": "optional", "purpose": "test lane: cross-language reporter (10/02.20)"},
    {"name": "openssl", "scope": "optional", "purpose": "test lane: mTLS certificate generation (05)"},
]


def files(root=ROOT):
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in EXCLUDE_DIRS)
        for f in sorted(fns):
            if f.endswith((".pyc",)) or f == "SBOM.cdx.json":
                continue
            p = os.path.join(dp, f)
            yield os.path.relpath(p, os.path.dirname(root)).replace(os.sep, "/"), p


def build(version="5.1.0") -> dict:
    comps = []
    for rel, p in files():
        with open(p, "rb") as fh:
            comps.append({"type": "file", "name": rel, "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(fh.read()).hexdigest()}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "gap09_unified_observability", "version": version},
                         "properties": [{"name": "runtime.requires", "value": "CPython>=3.10 (stdlib only)"}]},
            "components": comps, "properties": [{"name": f"lane.{l['name']}", "value": f"{l['scope']}: {l['purpose']}"} for l in LANES]}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "components", "evidence", "SBOM.cdx.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(build(), fh, indent=1, sort_keys=True)
    print(out)
