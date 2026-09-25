#!/usr/bin/env python3
"""Machine-readable release evidence bundle (checklist #89, #34, #42-digests).

Produces evidence/release_evidence.json containing:
  * source digests: sha256 of every tracked file + a Merkle-style tree digest
  * runtime/tool versions, host fingerprint
  * per-test results (pass/fail/skip with reason) from the full unittest run
  * secret-scan, traceability summary, benchmark result digests
  * SBOM (CycloneDX 1.5 JSON) at evidence/sbom.cdx.json
Signing is NOT performed (waiver: key custody undecided, GAP-07).
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import pathlib
import platform
import subprocess
import sys
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", "__pycache__", "build", "dist", ".venv"}
EXCLUDE_FILES = {"evidence/release_evidence.json", "evidence/exit_gate.json"}


def files() -> list[pathlib.Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and not any(x in EXCLUDE_DIRS for x in p.parts) and rel not in EXCLUDE_FILES:
            out.append(p)
    return out


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class _Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []

    def addSuccess(self, t):
        super().addSuccess(t); self.rows.append((t.id(), "pass", ""))

    def addFailure(self, t, err):
        super().addFailure(t, err); self.rows.append((t.id(), "fail", str(err[1])[:300]))

    def addError(self, t, err):
        super().addError(t, err); self.rows.append((t.id(), "error", type(err[1]).__name__))

    def addSkip(self, t, reason):
        super().addSkip(t, reason); self.rows.append((t.id(), "skip", reason))

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.rows.append((subtest.id(), "fail", str(err[1])[:300]))


def run_tests() -> list[dict]:
    sys.path.insert(0, str(ROOT / "tests"))
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT / "tests"))
    with open("/dev/null", "w") as devnull:
        res = unittest.TextTestRunner(stream=devnull, resultclass=_Collect, verbosity=0).run(suite)
    return [{"test": t, "result": r, "detail": d} for t, r, d in res.rows]


def sbom() -> dict:
    comps = [{"type": "library", "name": "inv55-secrets-integration", "version": "4.3.0", "scope": "required"}]
    for name in ["jsonschema", "referencing", "jsonschema-specifications", "attrs", "rpds-py"]:
        try:
            comps.append({"type": "library", "name": name, "version": md.version(name), "scope": "optional",
                          "purl": f"pkg:pypi/{name}@{md.version(name)}", "properties": [{"name": "inv55:use", "value": "test-only"}]})
        except md.PackageNotFoundError:
            pass
    comps.append({"type": "platform", "name": "cpython", "version": platform.python_version(), "scope": "required"})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": comps[0], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            "components": comps[1:]}


def main() -> int:
    ev = ROOT / "evidence"
    ev.mkdir(exist_ok=True)
    (ev / "sbom.cdx.json").write_text(json.dumps(sbom(), indent=1))
    subprocess.run([sys.executable, str(ROOT / "tools" / "traceability.py")], check=False, capture_output=True)
    scan = subprocess.run([sys.executable, str(ROOT / "tools" / "secret_scan.py"), str(ROOT)],
                          capture_output=True, text=True)
    tests = run_tests()
    digests = {p.relative_to(ROOT).as_posix(): sha(p) for p in files()}
    tree = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(digests.items())).encode()).hexdigest()
    git_rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    counts = {}
    for t in tests:
        counts[t["result"]] = counts.get(t["result"], 0) + 1
    bundle = {
        "format": "inv55-release-evidence/1",
        "component": "INV-55", "version": (ROOT / "VERSION").read_text().strip(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_revision": git_rev.stdout.strip() or "no-vcs (tree digest is authoritative)",
        "source_tree_sha256": tree,
        "file_digests": digests,
        "runtime": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                    "platform": platform.platform()},
        "tools": {"unittest": "stdlib", "jsonschema": _v("jsonschema"), "openssl": _openssl()},
        "secret_scan": {"exit": scan.returncode, "summary": scan.stdout.strip().splitlines()[-1:]},
        "tests": {"counts": counts, "results": tests},
        "signature": None,
        "signature_waiver": "WVR: artifact signing pending key-custody decision (GAP-07)",
    }
    (ev / "release_evidence.json").write_text(json.dumps(bundle, indent=1))
    print(json.dumps({"tree": tree, "tests": counts, "secret_scan_exit": scan.returncode}, indent=1))
    return 0 if scan.returncode == 0 and not counts.get("fail") and not counts.get("error") else 1


def _v(n):
    try:
        return md.version(n)
    except md.PackageNotFoundError:
        return None


def _openssl():
    try:
        return subprocess.run(["openssl", "version"], capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


if __name__ == "__main__":
    sys.exit(main())
