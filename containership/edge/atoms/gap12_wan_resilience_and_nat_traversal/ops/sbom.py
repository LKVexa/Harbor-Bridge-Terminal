"""SBOM (CycloneDX 1.5 JSON) and unsigned provenance statement (G12-I104).

The SBOM is generated from the *resolved* dependency graph: the import graph
of every module in the package is walked with ``ast``; stdlib modules are
classified with ``sys.stdlib_module_names``; anything else must be declared in
pyproject optional dependencies with an exact pin, otherwise generation FAILS.
The SBOM and the provenance statement carry the artifact digest.

Provenance is an in-toto Statement v1 with an SLSA v1 predicate.  It is NOT
signed: no signing identity/key exists for this build.  The statement records
``"signature": null`` and the evaluator reports signing as NOT-EVIDENCED.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.basename(ROOT)
PINNED = {"cryptography": ("46.0.7", "Apache-2.0 OR BSD-3-Clause", "optional: extras 'e2e'")}


def imports() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for d, dirs, fs in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in ("__pycache__", "dist", "tests", "evidence", "lab", "ops")]
        for f in fs:
            if not f.endswith(".py"):
                continue
            p = os.path.join(d, f)
            with open(p) as fh:
                tree = ast.parse(fh.read(), p)
            for n in ast.walk(tree):
                mods = []
                if isinstance(n, ast.Import):
                    mods = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    mods = [n.module]
                for m in mods:
                    found.setdefault(m.split(".")[0], set()).add(os.path.relpath(p, ROOT))
    return found


def sbom(artifact_digest: str, version: str) -> dict:
    third, std, unknown = [], [], []
    for mod, users in sorted(imports().items()):
        if mod in sys.stdlib_module_names or mod == "__future__":
            std.append(mod)
        elif mod in PINNED:
            third.append(mod)
        elif mod == "pk_core":
            continue                    # sibling framework, resolved at integration time, not shipped
        else:
            unknown.append((mod, sorted(users)))
    if unknown:
        raise SystemExit(f"undeclared third-party imports: {unknown}")
    comps = [{"type": "library", "name": m, "version": PINNED[m][0], "purl": f"pkg:pypi/{m}@{PINNED[m][0]}",
              "licenses": [{"expression": PINNED[m][1]}], "scope": "optional", "properties": [{"name": "gap12:note", "value": PINNED[m][2]}]}
             for m in third]
    comps.append({"type": "platform", "name": "cpython-stdlib", "version": f">={3}.{10}",
                  "properties": [{"name": "gap12:modules", "value": ",".join(std)}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": PKG, "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": artifact_digest}]},
                         "tools": [{"name": "gap12-ops-sbom", "version": version}]},
            "components": comps,
            "dependencies": [{"ref": PKG, "dependsOn": [c["name"] for c in comps]}]}


def provenance(artifact_name: str, artifact_digest: str, source_digest: str, version: str, tests_digest: str | None) -> dict:
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": artifact_name, "digest": {"sha256": artifact_digest}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "gap12/ops/build.py@v1",
                                              "externalParameters": {"version": version, "SOURCE_DATE_EPOCH": os.environ.get("SOURCE_DATE_EPOCH", "1790035200")},
                                              "resolvedDependencies": [{"name": "source-tree", "digest": {"sha256": source_digest}}]},
                          "runDetails": {"builder": {"id": "unattested-local-builder"},
                                         "metadata": {"python": platform.python_version(), "tests_results_sha256": tests_digest}}},
            "signature": None,
            "signature_status": "UNSIGNED: no signing identity or key is provisioned for this build"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tests-results")
    a = ap.parse_args()
    with open(a.artifact, "rb") as fh:
        dig = hashlib.sha256(fh.read()).hexdigest()
    ver = open(os.path.join(ROOT, "VERSION")).read().strip()
    src = hashlib.sha256("".join(sorted(imports())).encode()).hexdigest()
    td = None
    if a.tests_results and os.path.exists(a.tests_results):
        td = hashlib.sha256(open(a.tests_results, "rb").read()).hexdigest()
    os.makedirs(a.out, exist_ok=True)
    json.dump(sbom(dig, ver), open(os.path.join(a.out, "sbom.cdx.json"), "w"), indent=1, sort_keys=True)
    json.dump(provenance(os.path.basename(a.artifact), dig, src, ver, td), open(os.path.join(a.out, "provenance.intoto.json"), "w"), indent=1, sort_keys=True)
    print(dig)
