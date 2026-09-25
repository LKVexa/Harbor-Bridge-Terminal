"""M29 - CycloneDX 1.5 SBOM and dependency check (stdlib only).

    python tools/sbom.py                 # writes evidence/SBOM.cdx.json
    python tools/sbom.py --check-imports # fails if any module imports a non-stdlib, non-package module

Vulnerability scanning: with zero third-party dependencies the only runtime
component is CPython itself; the SBOM records the interpreter version so an
external CVE feed (not shipped) can match it.  The optional pk_core import in
component.py/contract.py is the single declared exception.
"""
from __future__ import annotations

import ast
import json
import pathlib
import platform
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_info import shipped_files, tree_digest  # noqa: E402

ALLOWED_EXTERNAL = {"pk_core"}  # optional, declared in ops/EXTERNAL_DEPENDENCIES.json
LOCAL = {"pln04_execution_plane", "helpers", "build_info", "perf", "fuzz", "sbom", "release_gate", "rtm"}


def foreign_imports() -> list[str]:
    std = set(sys.stdlib_module_names)
    bad = []
    for path in shipped_files():
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top not in std and top not in LOCAL and top not in ALLOWED_EXTERNAL:
                    bad.append(f"{path.relative_to(ROOT)}: {n}")
    return bad


def sbom() -> dict:
    digest, files = tree_digest()
    version = (ROOT / "VERSION").read_text().strip()
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, digest)}",
        "version": 1,
        "metadata": {"component": {"type": "library", "name": "pln04-execution-plane", "version": version,
                                   "hashes": [{"alg": "SHA-256", "content": digest.split(':')[1]}],
                                   "licenses": [{"license": {"name": "NOT DECLARED (M47 BLOCKED)"}}]}},
        "components": [
            {"type": "platform", "name": "cpython", "version": platform.python_version(), "scope": "required"},
            {"type": "library", "name": "pk_core", "version": "UNPINNED", "scope": "optional",
             "description": "certification framework; not supplied (M02 BLOCKED)"},
        ] + [{"type": "file", "name": f["path"], "hashes": [{"alg": "SHA-256", "content": f["sha256"]}]} for f in files],
    }


if __name__ == "__main__":
    bad = foreign_imports()
    if "--check-imports" in sys.argv:
        print("\n".join(bad) or "imports OK: stdlib + declared optional pk_core only")
        sys.exit(1 if bad else 0)
    out = ROOT / "evidence" / "SBOM.cdx.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(sbom(), indent=2))
    print(f"wrote {out.relative_to(ROOT)}; foreign imports: {bad or 'none'}")
