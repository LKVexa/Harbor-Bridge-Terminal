"""Local/CI lane runner (A4, C090).  Same entry point for developers and the GitHub workflow.

    python tools/ci.py [--lanes a,b,...] [--fuzz-seconds N] [--report release/ci_report.json]

Each lane reports PASS / FAIL / NOT_RUN (with reason).  A lane whose tests all SKIP is NOT_RUN,
never PASS.  Exit: 0 all required lanes PASS · 1 any FAIL · 3 a required lane NOT_RUN (INCOMPLETE).
The report binds results to the source-tree digest they exercised.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
PKG = ROOT.name
EXCLUDE_DIRS = {"__pycache__", ".git", "corpus"}
EXCLUDE_FILES = {"release/ci_report.json", "release/evidence.json", "release/MANIFEST.json", "release/sbom.cdx.json",
                 "release/provenance.json", "release/exit_gate.json", "release/perf_gate.json"}


def tree_digest() -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_dir() or set(p.relative_to(ROOT).parts) & EXCLUDE_DIRS or rel in EXCLUDE_FILES:
            continue
        h.update(rel.encode() + b"\0" + hashlib.sha256(p.read_bytes()).hexdigest().encode() + b"\n")
        n += 1
    return h.hexdigest(), n


def _unittest(mods: list[str], optimize: bool = False, env: dict | None = None) -> dict:
    cmd = [sys.executable] + (["-O"] if optimize else []) + ["-m", "unittest", "-v"] + \
          [f"{PKG}.{m}" for m in mods]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=PARENT, capture_output=True, text=True, env={**os.environ, **(env or {})})
    out = r.stderr
    ran = int(m.group(1)) if (m := re.search(r"Ran (\d+) test", out)) else 0
    skipped = int(m.group(1)) if (m := re.search(r"skipped=(\d+)", out)) else 0
    failures = sum(int(x) for x in re.findall(r"(?:failures|errors)=(\d+)", out))
    reasons = sorted(set(re.findall(r"skipped '([^']+)'", out)))
    if r.returncode != 0:
        status = "FAIL"
    elif ran == 0 or skipped == ran:
        status = "NOT_RUN"
    else:
        status = "PASS"
    return {"status": status, "ran": ran, "skipped": skipped, "failures": failures,
            "skip_reasons": reasons, "seconds": round(time.time() - t0, 2),
            "tail": out.strip().splitlines()[-3:]}


def _tool(args: list[str], ok_codes=(0,)) -> dict:
    t0 = time.time()
    r = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True)
    return {"status": "PASS" if r.returncode in ok_codes else "FAIL", "rc": r.returncode,
            "seconds": round(time.time() - t0, 2), "tail": (r.stdout + r.stderr).strip().splitlines()[-4:]}


UNIT = ["tests.unit.test_wasm_parser", "tests.unit.test_sfi_rewriter_verifier", "tests.unit.test_ops_modules",
        "tests.test_sfi_core"]
LANES = {
    "compile": (True, lambda a: _tool(["-m", "compileall", "-q", "."])),
    "unit": (True, lambda a: _unittest(UNIT)),
    "unit-optimized": (True, lambda a: _unittest(UNIT, optimize=True)),
    "security": (True, lambda a: _unittest(["tests.security.test_threats"])),
    "contract-schemas": (True, lambda a: _unittest(["tests.contract.test_contracts", "tests.contract.test_rtm"])),
    "fault": (True, lambda a: _unittest(["tests.fault.test_fault_injection"])),
    "concurrency": (True, lambda a: _unittest(["tests.concurrency.test_races"])),
    "integration-v8": (True, lambda a: _unittest(["tests.integration.test_engine_e2e"])),
    "fuzz-smoke": (True, lambda a: _unittest(["tests.fuzz.test_fuzz_parser"],
                                             env={"INV45_FUZZ_SECONDS": str(a.get("fuzz_seconds", 3))})),
    "rtm": (True, lambda a: _tool(["tools/rtm.py", "check"])),
    "derived-docs": (True, lambda a: _tool(["tools/gen_docs.py", "--check"])),
    "doc-links": (True, lambda a: _tool(["tools/check_docs.py"])),
    "pk-core-gate": (True, lambda a: _unittest(["tests.test_component"])),
    "license": (True, lambda a: {"status": "NOT_RUN", "reason": "no license selected (LICENSE-STATUS.md)"}),
}


def main() -> int:
    args = sys.argv[1:]
    sel = list(LANES)
    opts: dict = {}
    if "--lanes" in args:
        sel = args[args.index("--lanes") + 1].split(",")
    if "--fuzz-seconds" in args:
        opts["fuzz_seconds"] = float(args[args.index("--fuzz-seconds") + 1])
    report_path = ROOT / (args[args.index("--report") + 1] if "--report" in args else "release/ci_report.json")
    digest, nfiles = tree_digest()
    results = {}
    for name in sel:
        required, fn = LANES[name]
        res = fn(opts)
        res["required"] = required
        results[name] = res
        print(f"{name:18s} {res['status']:8s} {res.get('ran', '')!s:>5} {res.get('seconds', '')}s "
              f"{'; '.join(res.get('skip_reasons', [])) or res.get('reason', '')}")
    statuses = {r["status"] for r in results.values() if r["required"]}
    overall = "FAIL" if "FAIL" in statuses else ("INCOMPLETE" if "NOT_RUN" in statuses else "PASS")
    after, _ = tree_digest()
    rep = {"schema": "PK_SFI_CI_REPORT/1", "overall": overall, "source_tree_sha256": digest, "files": nfiles,
           "tree_unchanged_during_run": after == digest,
           "environment": {"python": platform.python_version(), "platform": platform.platform(),
                           "machine": platform.machine()},
           "lanes": results}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(f"OVERALL {overall}  tree {digest[:16]}…  report {report_path.relative_to(ROOT)}")
    return {"PASS": 0, "FAIL": 1}.get(overall, 3)


if __name__ == "__main__":
    sys.exit(main())
