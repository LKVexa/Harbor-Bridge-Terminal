"""Minimal CycloneDX-style SBOM (MC-088): the package, the vendored pk_core, the optional extra, and the
interpreter, each with hashes where they are files in this archive."""
from __future__ import annotations

import hashlib
import json
import sys

from ._refs import ROOT, load


def build() -> dict:
    prov = load("_vendor/PK_CORE_PROVENANCE.json")
    comps = [{"type": "library", "name": "pk_core", "version": "vendored", "scope": "required",
              "hashes": [{"alg": "SHA-256", "content": v, "file": k} for k, v in prov["files_sha256"].items()],
              "licenses": [{"license": {"name": prov["licence"]}}]},
             {"type": "library", "name": "cryptography", "version": ">=42", "scope": "optional",
              "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}]},
             {"type": "platform", "name": "CPython", "version": ">=3.10", "scope": "required"}]
    files = [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(ROOT.rglob("*.py")) if "__pycache__" not in p.parts and "_vendor" not in p.parts]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv27-unikernel-execution",
                                       "version": (ROOT / "VERSION").read_text().strip()}},
            "components": comps, "x-source-files": files}


def main(argv=None) -> int:
    (ROOT / "evidence" / "SBOM.json").write_text(json.dumps(build(), indent=1))
    print("SBOM written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
