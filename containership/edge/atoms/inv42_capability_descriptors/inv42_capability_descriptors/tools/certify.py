#!/usr/bin/env python3
"""MC-001 - certification profile runner.

    python tools/certify.py --profile dev            # pk_core optional, skips allowed
    python tools/certify.py --profile certification  # pk_core REQUIRED, zero skips

In the certification profile a missing/incompatible pk_core, any skipped test or
any unexpected failure is a hard failure (exit 2) with a remediation message.
Writes evidence/certify_<profile>.json (counts, env fingerprint, pk_core info).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = json.loads((PKG / "SPEC_MANIFEST.json").read_text())
REQ = MANIFEST["dependencies"]["pk_core"]
REQUIRED_API = REQ["required_api"]


def pk_core_probe() -> dict:
    for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(PKG.parent.parent), str(PKG.parent)]):
        if p not in sys.path:
            sys.path.append(p)
    try:
        mod = importlib.import_module("pk_core")
    except ModuleNotFoundError:
        return {"present": False, "error": "pk_core not importable"}
    info = {"present": True, "version": getattr(mod, "__version__", None), "file": getattr(mod, "__file__", None)}
    missing = []
    for dotted in REQUIRED_API:
        modname, _, attr = dotted.rpartition(".")
        try:
            if not hasattr(importlib.import_module(modname), attr):
                missing.append(dotted)
        except Exception:  # noqa: BLE001
            missing.append(dotted)
    info["missing_api"] = missing
    ver = info["version"]
    info["version_ok"] = bool(ver) and ver in REQ["supported_versions"]
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["dev", "certification"], default="dev")
    args = ap.parse_args()
    probe = pk_core_probe()
    cert = args.profile == "certification"
    problems = []
    if cert:
        if not probe["present"]:
            problems.append(f"pk_core missing: install {REQ['requirement']} (see {REQ['source']}) "
                            "or set PK_CORE_PATH; certification never skips framework tests")
        else:
            if probe["missing_api"]:
                problems.append(f"pk_core API incompatible, missing {probe['missing_api']}")
            if not probe["version_ok"]:
                problems.append(f"pk_core version {probe['version']!r} not in {REQ['supported_versions']}")
    suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), top_level_dir=str(PKG / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    opt = subprocess.run([sys.executable, "-O", "-m", "unittest", "discover", "-s", str(PKG / "tests")],
                         capture_output=True, text=True)
    skipped = len(result.skipped)
    if cert and skipped:
        problems.append(f"{skipped} skipped test(s) in certification profile: "
                        + "; ".join(f"{t.id()}: {why}" for t, why in result.skipped))
    if not result.wasSuccessful():
        problems.append("test failures/errors")
    if opt.returncode != 0:
        problems.append("optimized-mode (python -O) run failed")
    src_digest = hashlib.sha256()
    for f in sorted(PKG.rglob("*.py")):
        if "evidence" not in f.parts:
            src_digest.update(f.relative_to(PKG).as_posix().encode() + b"\0" + f.read_bytes())
    ev = {
        "schema": "INV42_CERTIFY/1", "profile": args.profile, "ts": time.time(),
        "version": (PKG / "VERSION").read_text().strip(), "source_sha256": src_digest.hexdigest(),
        "python": platform.python_version(), "implementation": platform.python_implementation(),
        "platform": platform.platform(), "machine": platform.machine(),
        "ci_run": os.environ.get("GITHUB_RUN_ID"), "pk_core": probe,
        "tests": {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                  "skipped": skipped, "optimized_mode_ok": opt.returncode == 0},
        "passed": not problems, "problems": problems,
    }
    out = PKG / "evidence"
    out.mkdir(exist_ok=True)
    (out / f"certify_{args.profile}.json").write_text(json.dumps(ev, indent=2) + "\n")
    for p in problems:
        print(f"CERTIFY FAIL: {p}", file=sys.stderr)
    print(f"certify[{args.profile}]: {'PASS' if not problems else 'FAIL'}")
    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())
