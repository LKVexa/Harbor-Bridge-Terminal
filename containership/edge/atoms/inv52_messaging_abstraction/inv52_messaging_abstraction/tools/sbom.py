"""Emit a CycloneDX 1.5 SBOM for the repository (C090).  Stdlib only.

    python tools/sbom.py > sbom.cdx.json
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", ".git", "evidence"}


def main() -> None:
    version = (ROOT / "VERSION").read_text().strip()
    files = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & SKIP) and p.suffix != ".pyc":
            files.append({"type": "file", "name": rel.as_posix(),
                          "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]})
    bom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
        "metadata": {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "component": {"type": "library", "name": "inv52-messaging-abstraction",
                                   "version": version, "purl": f"pkg:pypi/inv52-messaging-abstraction@{version}"}},
        "components": [
            {"type": "container", "name": "daprio/daprd", "version": "1.17.x (candidate, unpinned patch)", "scope": "optional",
             "licenses": [{"license": {"id": "Apache-2.0"}}], "description": "sidecar referenced by deploy/dapr (not bundled)"},
            *files,
        ],
        "dependencies": [{"ref": "inv52-messaging-abstraction", "dependsOn": []}],
    }
    print(json.dumps(bom, indent=2))


if __name__ == "__main__":
    main()
