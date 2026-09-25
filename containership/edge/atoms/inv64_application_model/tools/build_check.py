"""Reproducible wheel/sdist build + clean-install smoke tests (MC-03; C031, C040, C093).

    python -m inv64_application_model.tools.build_check [--out evidence/BUILD.json] [--dist DIR]

1. copies the source tree to a scratch directory (building in-tree writes
   ``*.egg-info`` into the repository — a defect found in the INV-44 pass);
2. builds wheel and sdist through the PEP 517 hooks of the declared backend
   (``setuptools.build_meta``). Where ``python -m build`` is installed it is used
   with full build isolation; otherwise the hooks run in-process and the
   evidence records ``isolation: false`` (the session that produced 4.3.0 had
   no package-index access, so isolation could not be exercised there);
3. installs each artifact into its **own fresh virtual environment** (no
   network: ``--no-index``), then checks the same public API, version, schema
   data and ``pip check`` in both;
4. lints metadata: name, version == VERSION, Requires-Python, license
   expression present, classifiers match compatibility.json;
5. records artifact SHA-256s and backend versions.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = r"""
import json, importlib.resources as r, inv64_application_model as m
from inv64_application_model import manifest, service, release_gate
schemas = sorted(p.name for p in r.files("inv64_application_model").joinpath("schema").iterdir())
ex = json.loads(r.files("inv64_application_model").joinpath("examples/valid.json").read_text())
print(json.dumps({"version": m.__version__, "schemas": schemas, "valid_example": manifest.validate(ex) == [],
                  "digest": manifest.canonical(ex), "api": sorted(n for n in m.__all__)}))
"""


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _venv(d: Path, system_site: bool = False) -> Path:
    args = [sys.executable, "-m", "venv", str(d)] + (["--system-site-packages"] if system_site else [])
    subprocess.run(args, check=True, capture_output=True)
    return d / ("Scripts" if os.name == "nt" else "bin") / "python"


def build(dist: Path) -> dict:
    src = Path(tempfile.mkdtemp()) / "src"
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "dist", "build", "_build", "*.egg-info"))
    dist.mkdir(parents=True, exist_ok=True)
    isolation = importlib.util.find_spec("build") is not None
    if isolation:
        subprocess.run([sys.executable, "-m", "build", "--outdir", str(dist), str(src)], check=True, capture_output=True)
    else:
        code = ("import setuptools.build_meta as b, sys; d=sys.argv[1]; "
                "print(b.build_wheel(d)); print(b.build_sdist(d))")
        # SETUPTOOLS_USE_DISTUTILS=stdlib works around Debian's patched setuptools
        # ("AttributeError: install_layout") without changing the declared backend.
        env = dict(os.environ, SETUPTOOLS_USE_DISTUTILS="stdlib", PYTHONWARNINGS="ignore")
        subprocess.run([sys.executable, "-c", code, str(dist)], cwd=src, check=True, capture_output=True, env=env)
    import setuptools
    try:
        import wheel
        wv = wheel.__version__
    except ImportError:
        wv = None
    return {"isolation": isolation, "backend": "setuptools.build_meta", "setuptools": setuptools.__version__,
            "wheel": wv, "python": sys.version.split()[0]}


def smoke(artifact: Path, *, sdist: bool) -> dict:
    with tempfile.TemporaryDirectory() as d:
        py = _venv(Path(d) / "venv", system_site=sdist)  # sdist needs setuptools to build offline
        cmd = [str(py), "-m", "pip", "install", "--no-index", "--no-deps", "-q"]
        if sdist:
            cmd.append("--no-build-isolation")
        env = dict(os.environ, SETUPTOOLS_USE_DISTUTILS="stdlib", PYTHONWARNINGS="ignore")
        r = subprocess.run(cmd + [str(artifact)], capture_output=True, text=True, env=env)
        if r.returncode:
            return {"artifact": artifact.name, "ok": False, "error": r.stderr[-800:]}
        out = subprocess.run([str(py), "-c", SMOKE], capture_output=True, text=True, cwd=d)
        chk = subprocess.run([str(py), "-m", "pip", "check"], capture_output=True, text=True)
        if out.returncode:
            return {"artifact": artifact.name, "ok": False, "error": out.stderr[-800:]}
        return {"artifact": artifact.name, "ok": True, "pip_check": chk.returncode == 0 or "No broken" in chk.stdout,
                "pip_check_output": (chk.stdout + chk.stderr).strip()[-300:], **json.loads(out.stdout)}


def lint(wheel_path: Path) -> list[str]:
    problems = []
    with zipfile.ZipFile(wheel_path) as z:
        meta_name = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        meta = z.read(meta_name).decode()
        names = z.namelist()
    version = (ROOT / "VERSION").read_text().strip()
    compat = json.loads((ROOT / "compatibility.json").read_text())
    if f"Version: {version}" not in meta:
        problems.append("wheel version != VERSION")
    if f"Requires-Python: >={compat['python']['min']}" not in meta:
        problems.append("Requires-Python differs from compatibility.json")
    if "License: LicenseRef-" not in meta and "License-Expression" not in meta:
        problems.append("license metadata missing")
    for v in compat["python"]["tested_in_ci"]:
        if f"Programming Language :: Python :: {v}" not in meta:
            problems.append(f"classifier for {v} missing")
    for required in ("inv64_application_model/schema/app-v1.schema.json", "inv64_application_model/VERSION",
                     "inv64_application_model/LICENSING.md", "inv64_application_model/NOTICE"):
        if required not in names:
            problems.append(f"wheel lacks {required}")
    if any(".egg-info" in n for n in names):
        problems.append("egg-info leaked into wheel")
    return problems


def run(dist: Path) -> dict:
    info = build(dist)
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    res = {"schema": "PK_APP_BUILD/1", "build": info,
           "artifacts": [{"name": p.name, "sha256": _sha(p), "bytes": p.stat().st_size} for p in wheels + sdists]}
    if len(wheels) != 1 or len(sdists) != 1:
        res.update(result="FAIL", error="expected one wheel and one sdist")
        return res
    w, s = smoke(wheels[0], sdist=False), smoke(sdists[0], sdist=True)
    res["installs"] = [w, s]
    res["metadata_problems"] = lint(wheels[0])
    same = w.get("ok") and s.get("ok") and all(w.get(k) == s.get(k) for k in ("version", "schemas", "api", "digest"))
    res["wheel_sdist_equivalent"] = bool(same)
    res["in_tree_clean"] = not any(ROOT.glob("*.egg-info"))
    res["result"] = "PASS" if same and not res["metadata_problems"] and res["in_tree_clean"] and \
        w.get("pip_check") and s.get("pip_check") else "FAIL"
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--dist", default=None)
    a = ap.parse_args(argv)
    dist = Path(a.dist) if a.dist else Path(tempfile.mkdtemp()) / "dist"
    res = run(dist)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: res.get(k) for k in ("result", "wheel_sdist_equivalent", "metadata_problems")}), "dist:", dist)
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
