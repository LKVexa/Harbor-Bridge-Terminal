"""Minimal CycloneDX 1.5 JSON SBOM + import audit (checklist #34).

Walks every ``*.py`` under the package, collects top-level imports, and
classifies each as stdlib / first-party / third-party.  Any third-party import
in runtime code fails the check (the package declares zero dependencies).
Deterministic: no timestamps or serial numbers.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
FIRST_PARTY = {"inv55_secrets_integration", "pk_core"} | {p.stem for p in PKG.rglob("*.py")}


def imports():
    found = {}
    for p in sorted(PKG.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                found.setdefault(n.split(".")[0], set()).add(p.relative_to(PKG).as_posix())
    return found


def classify(mod):
    if mod in FIRST_PARTY:
        return "first-party"
    if mod in sys.stdlib_module_names:
        return "stdlib"
    return "third-party"


def build(version: str):
    imp = imports()
    third = {m: sorted(f) for m, f in imp.items() if classify(m) == "third-party"}
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts and "evidence" not in p.parts)
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(PKG).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "library", "name": "inv55-secrets-integration", "version": version,
                                   "hashes": [{"alg": "SHA-256", "content": h.hexdigest()}]}},
        "components": [],   # zero third-party components by declaration and by audit below
        "properties": [{"name": "inv55:stdlib-imports", "value": ",".join(sorted(m for m in imp if classify(m) == "stdlib"))},
                       {"name": "inv55:third-party-imports", "value": json.dumps(third, sort_keys=True)},
                       {"name": "inv55:optional-estate-dependency", "value": "pk_core (not bundled)"}],
    }, third


if __name__ == "__main__":
    bom, third = build((PKG / "VERSION").read_text().strip())
    print(json.dumps(bom, indent=1))
    sys.exit(1 if third else 0)
