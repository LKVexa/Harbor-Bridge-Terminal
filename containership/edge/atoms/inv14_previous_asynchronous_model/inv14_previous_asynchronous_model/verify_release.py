"""Fail-closed release verifier for INV-14 v4.3.0 (component P2-27).

Runs every local gate, then evaluates every external gate.  Exit codes:
  0  all gates PASS (certifiable)
  1  a local gate FAILED (defect)
  2  local gates pass but at least one external gate is BLOCKED -- the release is
     NOT certified; the blockers are listed.  There is no "assumed pass" path.
Options: --skip-slow (omit fuzz/model-check/faults/soak/bench), --report FILE.
Set INV14_RELEASE=1 to make dependency-gated tests fail instead of skip.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
TESTS = ["test_polling.py", "test_p0_components.py", "test_p1_components.py", "test_p2_components.py", "test_integration_adjacent.py"]


def run(args, env=None):
    p = subprocess.run(args, cwd=HERE, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout + p.stderr)[-2000:]


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    slow = "--skip-slow" not in argv
    # --external-only evaluates only the external gates; used by fault scenario F5 so the
    # gate never re-enters its own test suite (defect D-04: unbounded recursion).
    external_only = "--external-only" in argv
    report_path = argv[argv.index("--report") + 1] if "--report" in argv else None
    py = sys.executable
    local, external = [], []

    def gate(name, args):
        rc, out = run(args)
        local.append({"gate": name, "result": "PASS" if rc == 0 else "FAIL", "rc": rc, "tail": out[-400:] if rc else ""})

    if external_only:
        slow = False
    if not external_only:
        _local_gates(gate, py, slow)

    sys.path.insert(0, str(HERE))
    sys.dont_write_bytecode = True
    import core_probe, governance, wasi_adapter  # noqa: E402
    pr = core_probe.probe()
    if pr["ok"] and not external_only:
        gate("test_component.py:normal", [py, "-B", "tests/test_component.py"])
        gate("test_component.py:optimized", [py, "-B", "-O", "tests/test_component.py"])
    return _finish(local, external, pr, py, report_path, core_probe, governance, wasi_adapter)


def _local_gates(gate, py, slow):
    gate("compile_all_sources", [py, "-B", "-c", "import pathlib,sys;[compile(p.read_text(),str(p),'exec') for p in pathlib.Path('.').rglob('*.py')]"])
    gate("manifest", [py, "-B", "tools/manifest.py", "--check"])
    gate("contracts_generated", [py, "-B", "tools/gen_contracts.py", "--check"])
    for t in TESTS:
        gate(f"{t}:normal", [py, "-B", f"tests/{t}"])
        gate(f"{t}:optimized", [py, "-B", "-O", f"tests/{t}"])
    if slow:
        gate("fuzz", [py, "-B", "tools/fuzz.py", "--iterations", "8000", "--seed", "11"])
        gate("interleave_model_check", [py, "-B", "tools/interleave.py"])
        gate("fault_injection", [py, "-B", "tools/faults.py"])
        gate("soak_burst", [py, "-B", "tools/soak.py", "--seconds", "3"])
        gate("bench_thresholds", [py, "-B", "tools/bench.py", "--n", "1000"])
        gate("sbom_stdlib_only", [py, "-B", "tools/sbom.py"])


def _finish(local, external, pr, py, report_path, core_probe, governance, wasi_adapter):
    external.append({"gate": "pk_core_pinned_and_compatible", "result": "PASS" if pr["ok"] else "BLOCKED", "code": pr["code"]})
    rc, out = run([py, "-B", "tools/sign.py", "verify", "--require-trusted"])
    external.append({"gate": "trusted_signature", "result": "PASS" if rc == 0 else "BLOCKED", "code": out.strip().splitlines()[-1] if out.strip() else str(rc)})
    rt = wasi_adapter.detect_runtimes()
    external.append({"gate": "wasi_0_2_interop", "result": "PASS" if rt["compiled_fixture"] and any(rt[k] for k in ("wasmtime_cli", "wasmtime_py", "jco")) else "BLOCKED",
                     "code": "NO_REAL_RUNTIME_OR_FIXTURE", "detected": rt})
    adj = os.environ.get("PK_ADJACENT_PATH")
    external.append({"gate": "adjacent_layers_INV13_INV15_GAP15", "result": "BLOCKED" if not adj else "SEE_TESTS", "code": "PK_ADJACENT_ABSENT" if not adj else "PRESENT"})
    gb = governance.production_blockers()
    external.append({"gate": "governance", "result": "PASS" if not gb else "BLOCKED", "code": gb})
    external.append({"gate": "independent_review", "result": "BLOCKED", "code": "NO_REVIEWER_RECORD",
                     "note": "the build and its own tests cannot approve their own evidence"})

    failed = [g for g in local if g["result"] != "PASS"]
    blocked = [g for g in external if g["result"] != "PASS"]
    rep = {"version": "4.3.0", "local": local, "external": external,
           "verdict": "FAIL" if failed else ("BLOCKED" if blocked else "PASS")}
    if report_path:
        pathlib.Path(report_path).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    for g in failed:
        print(f"FAIL {g['gate']} rc={g['rc']}\n{g['tail']}", file=sys.stderr)
    if failed:
        return 1
    if blocked:
        print(f"RELEASE BLOCKED: {len(local)} local gates run, all pass; external gates not satisfied: " +
              ", ".join(f"{g['gate']}={g['code']}" for g in blocked), file=sys.stderr)
        return 2
    print("INV-14 v4.3.0 release verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
