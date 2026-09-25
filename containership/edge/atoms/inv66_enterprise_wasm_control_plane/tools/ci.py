"""CI lane runner (MC-057, MC-061). Every lane reports PASS, FAIL or NOT_RUN — never a silent skip.

    python tools/ci.py [--out release/ci_report.json] [--fuzz-iters N] [--lanes a,b,...]

Overall result: PASS only if every lane is PASS.  Any NOT_RUN lane makes the overall INCOMPLETE
(exit 3); any FAIL makes it FAIL (exit 1).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
EXCLUDE_DIRS = {"__pycache__", ".git", "build", "dist"}


def run(cmd, env=None, cwd=ROOT, timeout=900):
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd), env={**os.environ, **(env or {})}, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)[-4000:], round(time.time() - t, 2)


def tree_digest() -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not set(rel.parts) & EXCLUDE_DIRS and not rel.as_posix().startswith("release/"):
            h.update(rel.as_posix().encode() + b"\0" + p.read_bytes())
            n += 1
    return h.hexdigest(), n


def lane_tests(name, starts, optimize=False, env=None):
    out = Path(tempfile.mkdtemp()) / f"{name}.json"
    cmd = [PY] + (["-O"] if optimize else []) + [str(ROOT / "tools" / "run_tests.py")] + \
        sum((["--start", s] for s in starts), []) + ["--out", str(out)]
    rc, log, secs = run(cmd, env=env)
    data = json.loads(out.read_text()) if out.exists() else {"summary": {}, "tests": {}}
    status = "PASS" if rc == 0 and data["summary"].get("pass", 0) > 0 else "FAIL"
    return {"status": status, "seconds": secs, "summary": data["summary"], "log_tail": log[-600:]}, data["tests"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "release" / "ci_report.json"))
    ap.add_argument("--fuzz-iters", default="1500")
    ap.add_argument("--lanes", default="")
    a = ap.parse_args(argv)
    want = set(filter(None, a.lanes.split(",")))
    lanes: dict[str, dict] = {}
    tests: dict[str, dict] = {}
    started = dt.datetime.now(dt.timezone.utc).isoformat()

    def do(name):
        return not want or name in want

    if do("compile"):
        rc, log, s = run([PY, "-m", "compileall", "-q", "-x", "(build|dist)", "."])
        lanes["compile"] = {"status": "PASS" if rc == 0 else "FAIL", "seconds": s, "log_tail": log}
        for d in ROOT.rglob("__pycache__"):
            shutil.rmtree(d, ignore_errors=True)
    suites = {"unit": ["tests/unit"], "legacy-engine": ["tests"], "contract": ["tests/contract"],
              "security": ["tests/security"], "fuzz": ["tests/fuzz"], "fault": ["tests/fault"],
              "concurrency": ["tests/concurrency"], "integration": ["tests/integration"], "disaster": ["tests/disaster"]}
    for name, starts in suites.items():
        if not do(name):
            continue
        if name == "legacy-engine":
            out = Path(tempfile.mkdtemp()) / "legacy.json"
            rc, log, s = run([PY, str(ROOT / "tools" / "run_tests.py"), "--module", "tests.test_control_plane",
                              "--module", "tests.test_component", "--out", str(out)])
            data = json.loads(out.read_text())
            leg = {k: v for k, v in data["tests"].items() if k.startswith(("tests.test_control_plane", "tests.test_component"))}
            tests.update(leg)
            pk = [v for k, v in leg.items() if k.startswith("tests.test_component")]
            lanes["legacy-engine"] = {"status": "PASS" if all(v["outcome"] == "pass" for k, v in leg.items()
                                                             if k.startswith("tests.test_control_plane")) else "FAIL",
                                      "seconds": s, "summary": {"tests": len(leg)}}
            lanes["pk-core-gate"] = {"status": "NOT_RUN" if all(v["outcome"] == "skip" for v in pk) else
                                     ("PASS" if all(v["outcome"] == "pass" for v in pk) else "FAIL"),
                                     "reason": "pk_core not bundled/importable (set PK_CORE_PATH)" if pk else "no tests"}
            continue
        res, t = lane_tests(name, starts, env={"INV66_FUZZ_ITERS": a.fuzz_iters} if name == "fuzz" else None)
        lanes[name] = res
        tests.update(t)
    if do("unit-optimized"):
        res, _ = lane_tests("unit-O", ["tests/unit", "tests/security", "tests/fault"], optimize=True)
        lanes["unit-optimized"] = res
    if do("lint"):
        if shutil.which("ruff"):
            rc, log, s = run(["ruff", "check", "--select", "E,F,W,B,S", "--ignore",
                              "E501,S101,S603,S607,S311,S108,B008,E701,E702,E731", "production", "tools"])
            lanes["lint"] = {"status": "PASS" if rc == 0 else "FAIL", "seconds": s, "log_tail": log[-800:], "tool": "ruff"}
        else:
            lanes["lint"] = {"status": "NOT_RUN", "reason": "ruff not installed"}
    if do("typecheck"):
        if shutil.which("mypy"):
            rc, log, s = run(["mypy", "--ignore-missing-imports", "production"])
            lanes["typecheck"] = {"status": "PASS" if rc == 0 else "FAIL", "seconds": s, "log_tail": log[-800:]}
        else:
            lanes["typecheck"] = {"status": "NOT_RUN", "reason": "mypy not installed"}
    if do("schema-drift"):
        rc, log, s = run([PY, "tools/gen_schemas.py", "--check"])
        lanes["schema-drift"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("requirements-drift"):
        rc, log, s = run([PY, "tools/gen_requirements.py", "--check"])
        lanes["requirements-drift"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("master"):
        rc, log, s = run([PY, "tools/gen_master.py", "--check"])
        lanes["master"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("docs"):
        rc, log, s = run([PY, "tools/check_docs.py"])
        lanes["docs"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("observability"):
        rc, log, s = run([PY, "tools/check_observability.py"])
        lanes["observability"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("secrets-scan"):
        rc, log, s = run([PY, "tools/check_secrets.py"])
        lanes["secrets-scan"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("package"):
        rc, log, s = run([PY, "tools/check_package.py"], timeout=600)
        lanes["package"] = {"status": "PASS" if rc == 0 else "FAIL", "seconds": s, "log_tail": log[-1500:]}
    if do("waivers"):
        rc, log, s = run([PY, "tools/check_waivers.py"])
        lanes["waivers"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
    if do("perf-gate"):
        bench = ROOT / "release" / "bench.json"
        if bench.exists():
            rc, log, s = run([PY, "tools/perf_gate.py", str(bench)])
            lanes["perf-gate"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log}
        else:
            lanes["perf-gate"] = {"status": "NOT_RUN", "reason": "no release/bench.json (run tools/bench.py)"}
    if do("review"):
        rc, log, s = run([PY, "tools/review.py", "--config", "config/examples/base.json", "config/examples/prod.json",
                          "--out", str(ROOT / "release" / "review.json")])
        lanes["review"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log[-800:],
                           "note": "PASS = extraction ran; findings need human disposition"}
    if do("vuln-scan"):
        if shutil.which("pip-audit"):
            rc, log, s = run(["pip-audit", "-r", "constraints.txt"], timeout=300)
            lanes["vuln-scan"] = {"status": "PASS" if rc == 0 else "FAIL", "log_tail": log[-800:]}
        else:
            lanes["vuln-scan"] = {"status": "NOT_RUN", "reason": "pip-audit not installed / no advisory DB access"}
    if do("license"):
        lanes["license"] = {"status": "NOT_RUN", "reason": "no license selected (LICENSE-STATUS.md)"}
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
    statuses = {v["status"] for v in lanes.values()}
    overall = "FAIL" if "FAIL" in statuses else ("INCOMPLETE" if "NOT_RUN" in statuses else "PASS")
    digest, nfiles = tree_digest()
    rep = {"schema": "PK_ECP_CI_REPORT/1", "started": started, "finished": dt.datetime.now(dt.timezone.utc).isoformat(),
           "overall": overall, "source_tree_sha256": digest, "source_files": nfiles,
           "environment": {"python": platform.python_version(), "os": platform.system(), "kernel": platform.release(),
                           "machine": platform.machine(),
                           "cryptography": __import__("cryptography").__version__},
           "lanes": lanes, "tests": tests,
           "test_totals": {k: sum(1 for t in tests.values() if t["outcome"] == k) for k in ("pass", "fail", "error", "skip")}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    w = max(len(k) for k in lanes)
    for k, v in lanes.items():
        print(f"{k:<{w}}  {v['status']}  {v.get('summary', '') or v.get('reason', '')}")
    print("overall:", overall, rep["test_totals"])
    return {"PASS": 0, "FAIL": 1, "INCOMPLETE": 3}[overall]


if __name__ == "__main__":
    sys.exit(main())
