"""MC67 / MC70 / MC75 — machine-readable release evidence, package SBOM, release manifest.

Usage (from the directory that contains the package):

    python -m inv02_container_substrate.tools.release_evidence [--out DIR] [--skip-integration]

Produces in ``DIR`` (default ``inv02_container_substrate/evidence``):

* ``test-results.json``   per-suite results in normal and ``-O`` modes, with skips and reasons
* ``sbom.cdx.json``       CycloneDX 1.5 SBOM for the package (stdlib-only: no third-party components)
* ``release-evidence.json`` source digests, artifact digests, interpreter/platform tuple,
                            governance-file checks, waiver state, and an overall gate verdict
and rewrites ``RELEASE_MANIFEST.sha256``.  Exit code is non-zero when a release gate fails.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import uuid
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REQUIRED_GOVERNANCE = ["MASTER.md", "README.md", "CHANGELOG.md", "VERSION", "pyproject.toml", "NOTICE",
                       "LICENSE-STATUS.md", "SECURITY.md", "OWNERS.yaml", "COMPATIBILITY.md",
                       "docs/adr/ADR-0001-substrate-architecture.md", "waivers/waivers.json",
                       "COMPONENT_STATUS.json", ".github/workflows/ci.yml"]
SUITES = ["tests"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


_RUNNER = r"""
import json, sys, unittest
class R(unittest.TextTestResult):
    def __init__(s, *a, **k):
        super().__init__(*a, **k); s.ok = []
    def addSuccess(s, t):
        super().addSuccess(t); s.ok.append(t.id())
loader = unittest.TestLoader()
suite = loader.discover(sys.argv[1], top_level_dir=sys.argv[2])
res = unittest.TextTestRunner(stream=open(__import__("os").devnull, "w"), resultclass=R, verbosity=0).run(suite)
print(json.dumps({"ran": res.testsRun, "passed": sorted(res.ok),
                  "failed": sorted(t.id() for t, _ in res.failures + res.errors),
                  "skipped": {t.id(): r for t, r in res.skipped}}))
"""


def run_suite(opt: bool, integration: bool) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    if not integration:
        env["INV02_SKIP_INTEGRATION"] = "1"
    cmd = [sys.executable] + (["-O"] if opt else []) + ["-c", _RUNNER, str(PKG / "tests"), str(PKG.parent)]
    r = subprocess.run(cmd, cwd=PKG.parent, env=env, capture_output=True, text=True, timeout=1800)
    try:
        data = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        data = {"ran": 0, "passed": [], "failed": ["<runner crashed>"], "skipped": {}}
    ok = r.returncode == 0 and not data["failed"] and data["ran"] > 0
    return {"mode": "optimized(-O)" if opt else "normal", "returncode": 0 if ok else 1, "ran": data["ran"],
            "passed": len(data["passed"]), "failed": data["failed"], "skipped": data["skipped"],
            "passed_ids": data["passed"], "stderr_tail": r.stderr[-1500:]}


def sbom(version: str, files: dict[str, str]) -> dict:
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
            "metadata": {"timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                         "component": {"type": "library", "name": "inv02-container-substrate", "version": version,
                                       "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(
                                           json.dumps(files, sort_keys=True).encode()).hexdigest()}]}},
            "components": [{"type": "platform", "name": "cpython", "version": platform.python_version(),
                            "scope": "required", "description": "runtime; package uses the standard library only"}],
            "dependencies": [{"ref": "inv02-container-substrate", "dependsOn": []}]}


def git_rev() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(PKG), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--skip-integration", action="store_true")
    ap.add_argument("--no-tests", action="store_true", help="digest-only refresh (never for a release)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    version = (PKG / "VERSION").read_text().strip()

    results = [] if a.no_tests else [run_suite(False, not a.skip_integration), run_suite(True, not a.skip_integration)]
    (out / "test-results.json").write_text(json.dumps(results, indent=2))

    files = {}
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and "__pycache__" not in rel and not rel.startswith("evidence/") and rel != "RELEASE_MANIFEST.sha256":
            files[rel] = sha256_file(p)
    (PKG / "RELEASE_MANIFEST.sha256").write_text("".join(f"{h}  {f}\n" for f, h in files.items()))
    (out / "sbom.cdx.json").write_text(json.dumps(sbom(version, files), indent=2))

    missing = [g for g in REQUIRED_GOVERNANCE if not (PKG / g).exists()]
    pyproject_ver = re.search(r'^version\s*=\s*"([^"]+)"', (PKG / "pyproject.toml").read_text(), re.M) \
        if (PKG / "pyproject.toml").exists() else None
    init_ver = re.search(r'__version__ = "([^"]+)"', (PKG / "__init__.py").read_text())
    now = _dt.datetime.now(_dt.timezone.utc).timestamp()
    waivers = json.loads((PKG / "waivers/waivers.json").read_text()).get("waivers", []) \
        if (PKG / "waivers/waivers.json").exists() else []
    expired = [w["waiver_id"] for w in waivers if w["expires_at"] <= now]
    gates = {
        "tests_pass_normal": bool(results) and results[0]["returncode"] == 0,
        "tests_pass_optimized": bool(results) and results[1]["returncode"] == 0,
        "governance_files_present": not missing,
        "versions_consistent": bool(pyproject_ver and init_ver) and pyproject_ver.group(1) == init_ver.group(1) == version,
        "no_expired_waivers": not expired,
    }
    evidence = {
        "schema": "inv02.release-evidence/1", "package": "inv02-container-substrate", "version": version,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(), "source_revision": git_rev(),
        "platform": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                     "system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "artifact_digests": files,
        "sbom_sha256": sha256_file(out / "sbom.cdx.json"),
        "test_results_sha256": sha256_file(out / "test-results.json"),
        "governance_missing": missing, "expired_waivers": expired, "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "note": "Local evidence. Estate-wide certification additionally requires pk_core conformance, the "
                "platform matrix in COMPATIBILITY.md, and signed archival (checklist E-01..E-08).",
    }
    (out / "release-evidence.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps({"verdict": evidence["verdict"], "gates": gates, "missing": missing}, indent=2))
    return 0 if evidence["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
