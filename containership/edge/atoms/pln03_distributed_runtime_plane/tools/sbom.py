"""CycloneDX 1.5 SBOM for the component (MC-056).  --check fails if SBOM.cdx.json is stale."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"SBOM.cdx.json", "evidence", "__pycache__", ".git"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & SKIP) and p.suffix != ".pyc":
            yield rel, p


def build() -> dict:
    version = (ROOT / "VERSION").read_text().strip()
    lock = json.loads((ROOT / "DEPENDENCIES.lock.json").read_text())
    comps = [{"type": "file", "name": str(rel).replace("\\", "/"),
              "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]}
             for rel, p in files()]
    for dep in lock["conformance_dependencies"]:
        comps.append({"type": "library", "name": dep["name"], "version": dep["version"] or "UNPINNED",
                      "scope": "optional", "properties": [{"name": "pk:status", "value": dep["status"]}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "pln03-distributed-runtime-plane",
                                       "version": version,
                                       "licenses": [{"license": {"name": "UNDECLARED (MC-056 blocked)"}}]}},
            "components": comps}


def main() -> int:
    bom = build()
    out = ROOT / "SBOM.cdx.json"
    text = json.dumps(bom, indent=2, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not out.exists() or out.read_text() != text:
            print("SBOM stale: run python tools/sbom.py")
            return 1
        print("SBOM current")
        return 0
    out.write_text(text)
    print(f"wrote {out.name} with {len(bom['components'])} components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
