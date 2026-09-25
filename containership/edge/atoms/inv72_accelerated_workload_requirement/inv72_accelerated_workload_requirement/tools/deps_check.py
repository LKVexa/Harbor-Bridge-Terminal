"""Dependency drift check + SBOM generation (C031, C093).

    python -m inv72_accelerated_workload_requirement.tools.deps_check [--sbom evidence/SBOM.json]

* Every runtime module (package root *.py) may import only the standard library or the package itself.
* requirements.lock pins must be exact (==) and match ops/APPROVED_TECH.json.
* Running interpreter must fall inside the supported Python range in ops/COMPATIBILITY_MATRIX.json.
* SBOM (CycloneDX-shaped JSON) lists every file with sha256 plus the pinned test dependency.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names)


def runtime_imports() -> dict[str, list[str]]:
    bad: dict[str, list[str]] = {}
    for p in sorted(ROOT.glob("*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            for m in mods:
                if m not in STDLIB and m != "__future__":
                    bad.setdefault(p.name, []).append(m)
    # component.py / contract.py are the pk_core conformance adapters (declared, W-001)
    for allowed in ("component.py", "contract.py"):
        if bad.get(allowed) == ["pk_core"] * len(bad.get(allowed, [])):
            bad.pop(allowed, None)
    return bad


def lock_pins() -> dict[str, str]:
    pins = {}
    for line in (ROOT / "requirements.lock").read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        if "==" not in line:
            raise SystemExit(f"C031 non-exact pin: {line}")
        n, v = line.split("==")
        pins[n.strip().lower()] = v.strip()
    return pins


def _vt(v):
    return tuple(int(x) for x in v.split("."))


def check() -> list[str]:
    out = []
    for f, mods in runtime_imports().items():
        out.append(f"C031 runtime module {f} imports non-stdlib {sorted(set(mods))}")
    approved = {i["name"].lower(): i["approved"] for i in json.loads((ROOT / "ops/APPROVED_TECH.json").read_text())["inventory"]}
    for n, v in lock_pins().items():
        if approved.get(n) != v:
            out.append(f"C031 lock pin {n}=={v} not in approved inventory ({approved.get(n)})")
    m = json.loads((ROOT / "ops/COMPATIBILITY_MATRIX.json").read_text())
    py = next(r for r in m["rows"] if r["component"] == "python")
    if not (_vt(py["min"]) <= _vt(platform.python_version()) <= _vt(py["max"])):
        out.append(f"C093 interpreter {platform.python_version()} outside supported {py['min']}..{py['max']}")
    return out


def sbom() -> dict:
    comps = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            comps.append({"type": "file", "name": str(p.relative_to(ROOT)),
                          "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(p.read_bytes()).hexdigest()}]})
    deps = [{"type": "library", "name": n, "version": v, "scope": "optional", "purl": f"pkg:pypi/{n}@{v}"}
            for n, v in lock_pins().items()]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5",
            "metadata": {"component": {"type": "library", "name": "inv72_accelerated_workload_requirement",
                                       "version": (ROOT / "VERSION").read_text().strip()},
                         "tools": [{"name": "tools/deps_check.py"}]},
            "components": deps + comps,
            "dependencies": [{"ref": "inv72_accelerated_workload_requirement", "dependsOn": []}],
            "notes": "runtime: Python standard library only; pk_core unpinned (W-001)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom")
    a = ap.parse_args(argv)
    problems = check()
    for p in problems:
        print("FAIL", p)
    if a.sbom:
        Path(a.sbom).write_text(json.dumps(sbom(), indent=1), encoding="utf-8")
        print("wrote", a.sbom)
    print("DEPS", "PASS" if not problems else "FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
