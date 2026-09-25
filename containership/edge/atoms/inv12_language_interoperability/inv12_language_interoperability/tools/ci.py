"""MC-054 CI conformance pipeline and MC-053 one-command integration environment.

Runs every gate in order, records each gate's command, exit status, duration
and output digest into ``evidence/ci_run.json``, and exits non-zero if any
*required* gate fails.  ``pk_core`` gates run only when ``PK_CORE_PATH`` (or an
importable ``pk_core``) is present; otherwise they are recorded as BLOCKED,
never as passed.

    python tools/ci.py            # full pipeline
    python tools/ci.py --quick    # smaller fuzz/differential/bench budgets
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
EV = ROOT / "evidence"
PY = sys.executable


def gates(quick):
    fz = "2000" if quick else "20000"
    rnd = "150" if quick else "1000"
    g = [
        ("syntax", [PY, "-m", "compileall", "-q", str(ROOT)], PARENT, True),
        ("lint-python", ["ruff", "check", "--select", "E,F,W,B,S", "--ignore", "E501,S101,S603,S607,S311,B904",
                         "--exclude", "fixtures", "."], ROOT, True),
        ("lint-go", ["go", "vet", "."], ROOT / "fixtures/go", True),
        ("lint-go-guest", ["go", "vet", "."], ROOT / "fixtures/wasm-guest", True),
        ("lint-rust", ["cargo", "clippy", "-q", "--release", "--offline", "--", "-D", "warnings"], ROOT / "fixtures/rust", True),
        ("lint-js", ["node", "--check", "fixtures/js/inv12.mjs"], ROOT, True),
        ("corpus-deterministic", [PY, "tools/gen_corpus.py", "--check"], ROOT, True),
        ("unit", [PY, "-m", "unittest", f"{ROOT.name}.tests.test_canon"], PARENT, True),
        ("unit-optimized", [PY, "-O", "-m", "unittest", f"{ROOT.name}.tests.test_canon"], PARENT, True),
        ("fuzz-smoke", [PY, "tools/fuzz.py", "--iterations", fz, "--out", str(EV / "fuzz.json")], ROOT, True),
        ("fuzz-regressions", [PY, "tools/fuzz.py", "--replay"], ROOT, True),
        ("language-matrix+differential", [PY, "tools/conformance.py", "--random", rnd, "--mutations", "5",
                                          "--out", str(EV / "conformance.json")], ROOT, True),
        ("wasm-guest-integration", [PY, "tools/wasm_gate.py"], ROOT, True),
        ("coverage", [PY, "tools/coverage_lite.py", "--min", "90", "--out", str(EV / "coverage.json")], ROOT, True),
        ("bench+slo+dos", [PY, "tools/bench.py"] + (["--quick"] if quick else []) + ["--out", str(EV / "bench.json")], ROOT, True),
        ("provenance+sbom", [PY, "tools/release.py", "--sbom-only"], ROOT, True),
        ("pipeline-negative-test", [PY, "tools/ci.py", "--negative-test"], ROOT, True),
    ]
    return g


def negative_test():
    """Run a synthetic pipeline: one failing gate, one missing tool, one passing gate."""
    global gates, _pk_probe
    real_gates, real_pk = gates, _pk_probe
    gates = lambda quick: [("must-fail", [PY, "-c", "raise SystemExit(3)"], ROOT, True),  # noqa: E731
                           ("missing-tool", ["inv12-no-such-tool", "--version"], ROOT, True),
                           ("must-pass", [PY, "-c", "pass"], ROOT, True)]
    _pk_probe = lambda: False  # noqa: E731
    out = EV / "ci_run.json"
    saved = out.read_text() if out.exists() else None
    try:
        sys.argv = [sys.argv[0]]
        try:
            main()
        except SystemExit as e:
            code = e.code
        doc = json.loads(out.read_text())
    finally:
        gates, _pk_probe = real_gates, real_pk
        if saved is not None:
            out.write_text(saved)
    ok = (code == 1 and doc["verdict"] == "FAIL" and doc["failed"] == ["must-fail"]
          and "missing-tool" in doc["blocked"])
    (EV / "ci_negative_test.json").write_text(json.dumps({"exit": code, "verdict": doc["verdict"],
                                                           "failed": doc["failed"], "blocked": doc["blocked"],
                                                           "pipeline_enforces_gates": ok}, indent=1) + "\n")
    print("negative pipeline test:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def pk_core_available():
    env_path = os.environ.get("PK_CORE_PATH")
    probe = subprocess.run([PY, "-c", "import pk_core"], capture_output=True,
                           env=dict(os.environ, PYTHONPATH=env_path or ""))
    return probe.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--negative-test", action="store_true",
                    help="prove the pipeline fails on a failing gate and blocks on a missing tool")
    a = ap.parse_args()
    if a.negative_test:
        return negative_test()
    EV.mkdir(exist_ok=True)
    results = []
    for name, cmd, cwd, required in gates(a.quick):
        if shutil.which(cmd[0]) is None and cmd[0] != PY:
            results.append({"gate": name, "status": "BLOCKED", "reason": f"{cmd[0]} not installed", "required": required})
            continue
        t0 = time.time()
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        out = (p.stdout + p.stderr)
        results.append({"gate": name, "cmd": " ".join(cmd[1:] if cmd[0] == PY else cmd), "exit": p.returncode,
                        "status": "PASS" if p.returncode == 0 else "FAIL", "seconds": round(time.time() - t0, 2),
                        "output_sha256": hashlib.sha256(out.encode()).hexdigest(), "tail": out[-600:],
                        "required": required})
        print(f"[{results[-1]['status']:7s}] {name} ({results[-1]['seconds']}s)", flush=True)
    if _pk_probe():
        env = dict(os.environ, PYTHONPATH=os.environ.get("PK_CORE_PATH", ""))
        for name, cmd in (("pk_core-conformance", [PY, "-m", "unittest", f"{ROOT.name}.tests.test_component"]),
                          ("pk_core-gate", [PY, "-m", "pk_core", "gate", "INV-12", "--out", str(EV / "PK_GATE_RESULTS.json")])):
            p = subprocess.run(cmd, cwd=PARENT, capture_output=True, text=True, env=env)
            results.append({"gate": name, "status": "PASS" if p.returncode == 0 else "FAIL", "exit": p.returncode,
                            "tail": (p.stdout + p.stderr)[-600:], "required": True})
    else:
        for name in ("pk_core-conformance", "pk_core-gate"):
            results.append({"gate": name, "status": "BLOCKED", "required": True,
                            "reason": "pk_core parent framework not present in this environment (MC-053)"})
    for r in results[-2:]:
        print(f"[{r['status']:7s}] {r['gate']}")
    failed = [r["gate"] for r in results if r["status"] == "FAIL"]
    blocked = [r["gate"] for r in results if r["status"] == "BLOCKED"]
    verdict = "FAIL" if failed else ("CONDITIONAL_PASS" if blocked else "PASS")
    doc = {"pipeline": "inv12-ci/1", "version": (ROOT / "VERSION").read_text().strip(),
           "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "quick": a.quick,
           "results": results, "failed": failed, "blocked": blocked, "verdict": verdict}
    (EV / "ci_run.json").write_text(json.dumps(doc, indent=1) + "\n")
    print("VERDICT:", verdict, "failed:", failed, "blocked:", blocked)
    sys.exit(1 if failed else 0)


_pk_probe = pk_core_available


if __name__ == "__main__":
    main()
