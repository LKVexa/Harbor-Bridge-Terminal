"""WP #62 - CycloneDX 1.5 SBOM for the PLN-06 source tree (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import platform
import uuid

PKG = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE = {"__pycache__", "evidence", ".git", "orig_snapshot", ".mypy_cache", ".ruff_cache"}


def files() -> list[pathlib.Path]:
    return sorted(p for p in PKG.rglob("*") if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE)
                  and p.suffix not in (".pyc",) and p.name not in ("sbom.cdx.json", "SHA256SUMS.txt"))


def build() -> dict:
    version = (PKG / "VERSION").read_text().strip()
    comps = [{"type": "file", "name": str(p.relative_to(PKG)),
              "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]} for p in files()]
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
        "metadata": {"component": {"type": "library", "name": "pln06-data-plane", "version": version,
                                   "licenses": [{"license": {"name": "UNDETERMINED (waiver W-010)"}}]},
                     "properties": [{"name": "runtime-dependencies", "value": "none (Python standard library only)"},
                                    {"name": "python", "value": ">=3.10"},
                                    {"name": "generator-python", "value": platform.python_version()}]},
        "components": [
            {"type": "framework", "name": "pk_core", "scope": "optional",
             "description": "certification framework; not resolvable (waiver W-008)"},
            *comps],
        "dependencies": [{"ref": "pln06-data-plane", "dependsOn": []}],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "sbom.cdx.json"))
    a = ap.parse_args(argv)
    pathlib.Path(a.out).write_text(json.dumps(build(), indent=2))
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
