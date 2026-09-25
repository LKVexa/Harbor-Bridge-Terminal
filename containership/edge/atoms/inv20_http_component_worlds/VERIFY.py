"""Release-oriented verification entry point for INV-20 (fails closed).

Run from the directory that CONTAINS the package, or from inside it:

    python VERIFY.py            # or: python -m inv20_http_component_worlds.VERIFY

Stages (every stage always runs; none can be skipped by flag):
  1 version consistency        5 seeded fuzz smoke (3 seeds)
  2 bytecode compile           6 benchmark regression gate + dispatch SLO
  3 WIT validity + freshness   7 build wheel, inspect, clean-room install + tests on installed artifact
  4 dependency-independent     8 pk_core probe; full conformance (normal + python -O) when available
    suites (normal + python -O) 9 evidence bundle for C001-C100 + independent gate

Exit 0: GO (all 100 requirements PASS, signed, fresh).       Exit 1: a check FAILED or evidence is stale/tampered.
Exit 2: BLOCKED — nothing failed, but mandatory items (pk_core, upstream WIT pin, signing, owners, drills)
        cannot be closed in this environment. BLOCKED is never reported as PASS.
"""
from __future__ import annotations

import compileall
import json
import pathlib
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parent
ROOT = PKG.parent
NAME = PKG.name
SUITES = ["test_runtime", "test_protocol", "test_egress", "test_identity", "test_config", "test_aio", "test_ops",
          "test_evidence"]


def py(*args: str, opt: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable] + (["-O"] if opt else []) + list(args)
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def stage(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""), flush=True)
    return ok


def main() -> int:
    results = {}
    r = py("-c", f"from {NAME}.tools.release import version_check; print(version_check())")
    results["version"] = stage("1 version consistency", r.returncode == 0, (r.stdout or r.stderr).strip()[-120:])
    results["compile"] = stage("2 compile", bool(compileall.compile_dir(str(PKG), quiet=1, force=False)))
    r = py("-m", f"{NAME}.witgen", "--check")
    results["wit"] = stage("3 WIT validity + freshness", r.returncode == 0, (r.stdout or r.stderr).strip())
    mods = [f"{NAME}.tests.{s}" for s in SUITES]
    r1, r2 = py("-m", "unittest", *mods), py("-m", "unittest", *mods, opt=True)
    results["suites"] = stage("4 dependency-independent suites (normal, -O)", r1.returncode == 0 and r2.returncode == 0,
                              r1.stderr.strip().splitlines()[-1] + " / -O: " + r2.stderr.strip().splitlines()[-1])
    fz = [py("-m", f"{NAME}.fuzz.fuzz_parsers", "--iterations", "8000", "--seed", str(s)) for s in (1, 2, 3)]
    results["fuzz"] = stage("5 fuzz smoke", all(f.returncode == 0 for f in fz),
                            f"{sum(json.loads(f.stdout)['iterations'] for f in fz if f.stdout)} inputs")
    b = py("-m", f"{NAME}.bench.run_bench", "--out", str(PKG / "bench" / "last_run.json"))
    results["bench"] = stage("6 benchmark gate", b.returncode == 0, "see bench/last_run.json")
    rel = py("-m", f"{NAME}.tools.release", "--out", str(PKG / "dist"))
    results["clean_room"] = stage("7 build + clean-room install", rel.returncode == 0, (rel.stdout or rel.stderr).strip()[-160:])
    probe = json.loads(py("-c", f"import json;from {NAME}.pk_compat import probe;print(json.dumps(probe()))").stdout)
    pk_ok = probe["status"] == "PASS"
    if pk_ok:
        c1 = py("-m", "unittest", f"{NAME}.tests.test_component")
        c2 = py("-m", "unittest", f"{NAME}.tests.test_component", opt=True)
        results["conformance"] = stage("8 pk_core full conformance (normal, -O)", c1.returncode == 0 and c2.returncode == 0)
    else:
        print(f"[BLOCKED] 8 pk_core full conformance -- {probe['reason']}; 100-item conformance cannot be certified",
              file=sys.stderr, flush=True)
    local_ok = all(results.values())
    groups = [f"fuzz={'pass' if results['fuzz'] else 'fail'}", f"bench={'pass' if results['bench'] else 'fail'}",
              f"clean_room={'pass' if results['clean_room'] else 'fail'}", f"VERIFY={'pass' if local_ok else 'fail'}"]
    (PKG / "evidence" / "gate.json").unlink(missing_ok=True)
    g = py("-m", f"{NAME}.evidence_gate", "collect", *groups)
    try:
        verdict = json.loads((PKG / "evidence" / "gate.json").read_text())
    except (OSError, ValueError):
        verdict = {"verdict": "NO_GO", "reasons": ["evidence gate did not run: " + g.stderr[-300:]]}
    print(f"[{verdict.get('verdict')}] 9 evidence gate -- certification={verdict.get('counts')} "
          f"local-verification={verdict.get('local_counts')}")
    for reason in verdict.get("reasons", [])[:8]:
        print(f"      - {reason}")
    if not local_ok or verdict.get("verdict") == "NO_GO":
        return 1
    if not pk_ok or verdict.get("verdict") == "BLOCKED":
        print("BLOCKED: production certification not possible here; see evidence/traceability.json and "
              "MISSING_COMPONENTS.md for the blocking work items.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
