#!/usr/bin/env python3
"""CycloneDX 1.5 SBOM generator (component 65).

  python tools/sbom.py [--out sbom.cdx.json]

Inventories every file shipped in the package (SHA-256), the declared Python
runtime requirement, the zero third-party runtime dependencies, and the
optional/external integration dependencies (pk_core, Kubernetes API server)
as ``excluded`` scope so consumers see what the deployment must supply.
Deterministic: output depends only on package content and VERSION.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import uuid

PKG = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {"__pycache__", ".git", "dist", "evidence", ".mypy_cache", ".ruff_cache"}


def shipped_files() -> list[pathlib.Path]:
    return sorted(p for p in PKG.rglob("*") if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS)
                  and p.suffix not in (".pyc",) and p.name != "MANIFEST.sha256")


def build() -> dict:
    version = (PKG / "VERSION").read_text().strip()
    files = []
    digest = hashlib.sha256()
    for f in shipped_files():
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        digest.update(f"{f.relative_to(PKG).as_posix()}:{h}\n".encode())
        files.append({"type": "file", "name": f.relative_to(PKG).as_posix(),
                      "hashes": [{"alg": "SHA-256", "content": h}]})
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"urn:pk:inv04:{version}:{digest.hexdigest()}")
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}", "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv04-current-orchestration", "version": version,
                                   "hashes": [{"alg": "SHA-256", "content": digest.hexdigest()}]},
                     "properties": [{"name": "inv04:runtime-dependencies", "value": "none (stdlib only)"}]},
        "components": [
            {"type": "platform", "name": "cpython", "version": ">=3.10", "scope": "required"},
            {"type": "library", "name": "pk_core", "version": "4.0.*", "scope": "optional",
             "description": "Estate conformance framework (not shipped; see tools/pk_core_gate.py)"},
            {"type": "platform", "name": "kubernetes-api-server", "version": "1.28-1.33", "scope": "excluded",
             "description": "External authority for production; adapter not shipped (ADR-0001)"},
            *files,
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True)
    if a.out:
        pathlib.Path(a.out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
