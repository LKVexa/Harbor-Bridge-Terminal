"""Build, digest, SBOM, provenance and clean-room verification (checklist components 9 and 26).

    python -m inv20_http_component_worlds.tools.release --out dist/
        1. version consistency check (VERSION, _version, pyproject, CHANGELOG, README)
        2. build wheel + sdist offline (pinned backend, --no-build-isolation)
        3. verify wheel contents (metadata + no evidence/secrets/pyc)
        4. SHA-256 digests; CycloneDX 1.5 SBOM; build provenance (in-toto-style statement, UNSIGNED)
        5. clean-room: fresh venv, install the wheel with --no-index, run the dependency-independent
           suites against the *installed* artifact (not the source tree)
Signing is BLOCKED until an approved signing service exists: provenance carries "signature": null
and the evidence gate treats unsigned artifacts as non-PASS for C090/C094/C100.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile

PKG = pathlib.Path(__file__).resolve().parents[1]
SUITES = ["test_runtime", "test_protocol", "test_egress", "test_identity", "test_config", "test_aio", "test_ops"]
EXCLUDE = re.compile(r"(^|/)(evidence|dist|__pycache__|build|fuzz/crashes)(/|$)|\.egg-info|\.pyc$|^bench/last_run\.json$|^SOURCE_REVISION$")
FORBIDDEN_IN_DIST = re.compile(r"(^|/)(evidence|dist|fuzz/crashes)/|\.pyc$|\.pem$|\.key$|\.env$")


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def version_check() -> str:
    ns: dict = {}
    exec((PKG / "_version.py").read_text(), ns)
    v = ns["__version__"]
    problems = []
    if (PKG / "VERSION").read_text().strip() != v:
        problems.append("VERSION")
    if tomllib.loads((PKG / "pyproject.toml").read_text())["project"]["version"] != v:
        problems.append("pyproject.toml")
    if f"## {v}" not in (PKG / "CHANGELOG.md").read_text():
        problems.append("CHANGELOG.md")
    if f"**Version:** {v}" not in (PKG / "README.md").read_text():
        problems.append("README.md")
    if problems:
        raise SystemExit(f"version drift in: {', '.join(problems)} (canonical {v})")
    return v


def build(out: pathlib.Path) -> list:
    """Build from a pristine copy of the tree (no __pycache__, build/, evidence/) so local state never leaks."""
    out.mkdir(parents=True, exist_ok=True)
    # SETUPTOOLS_USE_DISTUTILS=stdlib: works around Debian-patched distutils (install_layout AttributeError).
    env = dict(os.environ, SOURCE_DATE_EPOCH="1767225600", PYTHONHASHSEED="0", SETUPTOOLS_USE_DISTUTILS="stdlib",
               PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory() as d:
        stage_dir = pathlib.Path(d) / PKG.name
        for p in sorted(PKG.rglob("*")):
            rel = p.relative_to(PKG).as_posix()
            if p.is_file() and not EXCLUDE.search(rel):
                dst = stage_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                        "-w", str(out), str(stage_dir)], check=True, env=env, capture_output=True)
    return sorted(out.glob("*.whl"))


def inspect_wheel(whl: pathlib.Path) -> dict:
    with zipfile.ZipFile(whl) as z:
        names = z.namelist()
    bad = [n for n in names if FORBIDDEN_IN_DIST.search(n)]
    meta = [n for n in names if n.endswith(".dist-info/METADATA")]
    required = ["inv20_http_component_worlds/wit/inv20.wit", "inv20_http_component_worlds/_wit_generated.py",
                "inv20_http_component_worlds/components.json", "inv20_http_component_worlds/CHECKLIST.json"]
    missing = [r for r in required if r not in names]
    return {"files": len(names), "forbidden": bad, "metadata": bool(meta), "missing_required": missing,
            "ok": not bad and bool(meta) and not missing}


def sbom(v: str, whl: pathlib.Path) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "component": {"type": "library", "name": "inv20-http-component-worlds", "version": v,
                                       "hashes": [{"alg": "SHA-256", "content": sha256(whl)}],
                                       "licenses": [{"license": {"name": "UNDECLARED"}}]}},
            "components": [
                {"type": "framework", "name": "python-stdlib", "version": platform.python_version(),
                 "licenses": [{"license": {"id": "PSF-2.0"}}]},
                {"type": "library", "name": "pk_core", "version": "UNRESOLVED", "scope": "optional",
                 "description": "release-gate conformance dependency; not resolvable in this build (BLOCKED)"},
                {"type": "data", "name": "wasi:http WIT", "version": "UNRESOLVED",
                 "description": "upstream WIT not vendored; see wit/wit.lock"}],
            "dependencies": [{"ref": "inv20-http-component-worlds", "dependsOn": ["python-stdlib"]}]}


def source_digest() -> str:
    h = hashlib.sha256()
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and not EXCLUDE.search(rel):
            h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def clean_room(whl: pathlib.Path) -> dict:
    with tempfile.TemporaryDirectory() as d:
        venv = pathlib.Path(d) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        r1 = subprocess.run([str(py), "-m", "pip", "install", "--no-index", "--no-deps", str(whl)],
                            capture_output=True, text=True)
        mods = [f"inv20_http_component_worlds.tests.{s}" for s in SUITES]
        r2 = subprocess.run([str(py), "-I", "-m", "unittest", *mods], capture_output=True, text=True, cwd=d)
        r3 = subprocess.run([str(py), "-I", "-c", "import inv20_http_component_worlds as p;print(p.__file__)"],
                            capture_output=True, text=True, cwd=d)
        return {"install_rc": r1.returncode, "tests_rc": r2.returncode, "tests_tail": r2.stderr.strip().splitlines()[-3:],
                "imported_from": r3.stdout.strip(), "installed_artifact": "site-packages" in r3.stdout,
                "ok": r1.returncode == 0 and r2.returncode == 0 and "site-packages" in r3.stdout}


def write_sums() -> int:
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and not EXCLUDE.search(p.relative_to(PKG).as_posix())
                   and p.name != "SHA256SUMS.txt")
    (PKG / "SHA256SUMS.txt").write_text("".join(f"{sha256(p)}  {p.relative_to(PKG).as_posix()}\n" for p in files))
    return len(files)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "dist"))
    ap.add_argument("--sums", action="store_true", help="regenerate SHA256SUMS.txt for the source tree and exit")
    a = ap.parse_args(argv)
    if a.sums:
        print(f"SHA256SUMS.txt: {write_sums()} files")
        return 0
    out = pathlib.Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    v = version_check()
    whl = build(out)[0]
    insp = inspect_wheel(whl)
    cr = clean_room(whl)
    bom = sbom(v, whl)
    (out / "sbom.cdx.json").write_text(json.dumps(bom, indent=1))
    prov = {"_type": "https://in-toto.io/Statement/v1", "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": whl.name, "digest": {"sha256": sha256(whl)}}],
            "predicate": {"buildDefinition": {"buildType": "inv20/tools/release.py@1",
                                              "externalParameters": {"version": v},
                                              "resolvedDependencies": [{"uri": "source-tree", "digest": {"sha256": source_digest()}}]},
                          "runDetails": {"builder": {"id": f"local:{platform.node() or 'unknown'}"},
                                         "metadata": {"python": sys.version.split()[0], "platform": platform.platform(),
                                                      "setuptools": "68.1.2", "wheel": "0.42.0"}}},
            "signature": None, "signature_status": "BLOCKED: no approved signing infrastructure"}
    (out / "provenance.json").write_text(json.dumps(prov, indent=1))
    manifest = {"schema": "INV20_BUILD/1", "version": v, "wheel": whl.name, "wheel_sha256": sha256(whl),
                "source_sha256": source_digest(), "inspection": insp, "clean_room": cr,
                "ok": insp["ok"] and cr["ok"]}
    (out / "build_manifest.json").write_text(json.dumps(manifest, indent=1))
    (out / "SHA256SUMS").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({k: manifest[k] for k in ("version", "wheel", "wheel_sha256", "ok")}))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
