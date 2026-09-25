"""Pin/SBOM check (C031, C045).  Fails if pyproject declares runtime deps, if
build deps float, if source imports a non-stdlib module, or if pinned protocol
ids disagree with the code.  Also emits a minimal CycloneDX-style SBOM."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names)


def check() -> dict:
    problems = []
    pins = json.loads((HERE / "PINS.json").read_text())
    py = (HERE / "pyproject.toml").read_text()
    m = re.search(r'^dependencies\s*=\s*\[(.*?)\]', py, re.M | re.S)
    if m is None or m.group(1).strip():
        problems.append("pyproject runtime dependencies must be an explicit empty list")
    for req in re.findall(r'requires\s*=\s*\[(.*?)\]', py, re.S):
        for dep in re.findall(r'"([^"]+)"', req):
            if "==" not in dep:
                problems.append(f"floating build dependency: {dep}")
            else:
                n, v = dep.split("==")
                if pins["build_dependencies"].get(n) != v:
                    problems.append(f"build pin mismatch {dep}")
    for p in sorted(HERE.glob("*.py")):
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for n in names:
                if n not in STDLIB and n != "pk_core":
                    problems.append(f"{p.name}: non-stdlib import {n}")
    pkg_src = (HERE / "shm_transport.py").read_text()
    if pins["transport"]["abi"] not in pkg_src:
        problems.append("transport ABI pin disagrees with code")
    return {"schema": "INV37_PIN_CHECK/1", "status": "FAIL" if problems else "PASS", "problems": problems}


def sbom() -> dict:
    comps = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and "artifacts" not in p.parts and p.suffix in (".py", ".json", ".toml", ".md", ".lock"):
            comps.append({"type": "file", "name": str(p.relative_to(HERE)),
                          "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5",
            "metadata": {"component": {"type": "library", "name": "inv37-bulk-data-plane",
                                       "version": (HERE / "VERSION").read_text().strip()}},
            "components": [{"type": "platform", "name": "cpython", "version": ">=3.10"}] + comps,
            "dependencies": []}


if __name__ == "__main__":
    r = check()
    out = HERE / "artifacts" / "certification"
    out.mkdir(parents=True, exist_ok=True)
    (out / "sbom.cdx.json").write_text(json.dumps(sbom(), indent=1))
    print(json.dumps(r, indent=1))
    sys.exit(0 if r["status"] == "PASS" else 1)
