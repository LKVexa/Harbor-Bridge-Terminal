"""INV-53 CI pipeline (component 92).  Stdlib only.

    python inv53_message_reliability/tools/ci.py [--pk-core PATH] [--out evidence/CI_EVIDENCE.json]

Lanes (each PASS / FAIL / NOT_RUN-with-reason; NOT_RUN is never PASS):
  compile      every .py compiles
  lint         tools/lint.py (R1-R8)
  schemas      generated schemas have not drifted
  unit         every tests/test_*.py except the pk_core suite, per-test results recorded
  optimized    the same suites under ``python -O``
  pk_core      conformance suite against the *pinned* pk_core (digest-checked)
  perf         benchmark run + regression gate against perf/THRESHOLDS.json
  reproducible release tarball built twice, byte-identical, SBOM emitted

The evidence file is bound to the source digest of the exact tree tested.  The
interpreter/platform of the run are recorded as evidence, never written into
tracked source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PKG / "tests"))
sys.dont_write_bytecode = True

from inv53_message_reliability.gate import source_digest  # noqa: E402

UNIT_SUITES = ["test_reliability", "test_durable", "test_security", "test_service", "test_protocol_config",
               "test_property_concurrency", "test_repository"]


def lane(fn):
    t = time.time()
    try:
        r = fn()
    except Exception as exc:  # a crashing lane is a FAIL, never a silent skip
        r = {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}
    r["seconds"] = round(time.time() - t, 3)
    return r


def compile_lane():
    bad = []
    for p in PKG.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as exc:
            bad.append(f"{p.name}:{exc.lineno}")
    return {"status": "FAIL" if bad else "PASS", "reason": ", ".join(bad)}


def run_cmd(args, env=None):
    return subprocess.run(args, capture_output=True, text=True, env={**os.environ, **(env or {}), "PYTHONDONTWRITEBYTECODE": "1"},
                          cwd=str(ROOT), timeout=900)


def lint_lane():
    r = run_cmd([sys.executable, str(PKG / "tools" / "lint.py")])
    out = json.loads(r.stdout)
    return {"status": "PASS" if r.returncode == 0 else "FAIL", "files": out["files"], "findings": out["findings"]}


def schemas_lane():
    r = run_cmd([sys.executable, "-m", "inv53_message_reliability", "schemas"])
    return {"status": "PASS" if r.returncode == 0 else "FAIL", "detail": r.stdout.strip()[-400:]}


class _Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes = {}

    def _id(self, test):
        mod, cls, meth = test.id().split(".")[-3:]
        return f"{mod}.py::{cls}::{meth}"

    def addSuccess(self, test):
        super().addSuccess(test); self.outcomes[self._id(test)] = "pass"

    def addFailure(self, test, err):
        super().addFailure(test, err); self.outcomes[self._id(test)] = "fail"

    def addError(self, test, err):
        super().addError(test, err); self.outcomes[self._id(test)] = "error"

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.outcomes[self._id(test)] = "skip"


def unit_lane():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromName(m) for m in UNIT_SUITES)
    with open(os.devnull, "w") as devnull:
        res = unittest.TextTestRunner(stream=devnull, resultclass=_Collect, verbosity=0).run(suite)
    bad = [k for k, v in res.outcomes.items() if v in ("fail", "error")]
    return {"status": "PASS" if not bad and res.testsRun else "FAIL", "tests_run": res.testsRun,
            "failed": bad, "skipped": [k for k, v in res.outcomes.items() if v == "skip"]}, res.outcomes


def optimized_lane():
    r = run_cmd([sys.executable, "-O", "-m", "unittest", *UNIT_SUITES], env={"PYTHONPATH": f"{PKG / 'tests'}{os.pathsep}{ROOT}"})
    tail = (r.stderr or "").strip().splitlines()[-3:]
    return {"status": "PASS" if r.returncode == 0 else "FAIL", "tail": tail}


def pk_core_lane(pk_path):
    lock = json.loads((PKG / "requirements" / "pk_core.lock.json").read_text())
    if not pk_path:
        return {"status": "NOT_RUN", "reason": "pk_core not supplied (--pk-core PATH); see requirements/pk_core.lock.json"}
    core = Path(pk_path) / "pk_core"
    if not core.is_dir():
        return {"status": "NOT_RUN", "reason": f"{core} does not exist"}
    h = hashlib.sha256()
    for p in sorted(core.glob("*.py")):
        h.update(p.name.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    got = h.hexdigest()
    if got != lock["content_sha256"]:
        return {"status": "FAIL", "reason": f"pk_core digest {got[:12]} does not match the pin {lock['content_sha256'][:12]}"}
    r = run_cmd([sys.executable, str(PKG / "tests" / "test_component.py")], env={"PK_CORE_PATH": str(pk_path)})
    ran = "skipped" not in (r.stderr or "")
    return {"status": "PASS" if r.returncode == 0 and ran else "FAIL", "pk_core_sha256": got,
            "tail": (r.stderr or "").strip().splitlines()[-3:]}


def perf_lane():
    from inv53_message_reliability import bench
    res = bench.run(n=1_000)
    thresholds = json.loads((PKG / "perf" / "THRESHOLDS.json").read_text())
    g = bench.gate(res, thresholds)
    status = "FAIL" if g["verdict"] == "FAIL" else "PASS"
    return {"status": status, "verdict": g["verdict"], "thresholds_status": g["thresholds_status"]}, g, res


def reproducible_lane():
    sys.path.insert(0, str(PKG / "tools"))
    import build_release
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        r1, r2 = build_release.build(Path(a)), build_release.build(Path(b))
        sbom = json.loads((Path(a) / "SBOM.cdx.json").read_text())
    same = r1["sha256"] == r2["sha256"]
    return {"status": "PASS" if same else "FAIL", "artifact": r1["artifact"], "sha256": r1["sha256"],
            "members": r1["members"], "sbom_components": [c["name"] for c in sbom["components"]]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pk-core", default=os.environ.get("PK_CORE_PATH"))
    ap.add_argument("--out", default=str(PKG / "evidence" / "CI_EVIDENCE.json"))
    ap.add_argument("--skip-perf", action="store_true")
    a = ap.parse_args(argv)
    digest_before = source_digest(PKG)
    lanes, tests = {}, {}
    lanes["compile"] = lane(compile_lane)
    lanes["lint"] = lane(lint_lane)
    lanes["schemas"] = lane(schemas_lane)
    t0 = time.time()
    u, tests = unit_lane()
    u["seconds"] = round(time.time() - t0, 3)
    lanes["unit"] = u
    lanes["optimized"] = lane(optimized_lane)
    lanes["pk_core"] = lane(lambda: pk_core_lane(a.pk_core))
    perf_gate, bench_result = None, None
    if a.skip_perf:
        lanes["perf"] = {"status": "NOT_RUN", "reason": "--skip-perf"}
    else:
        p, perf_gate, bench_result = perf_lane()
        lanes["perf"] = p
    lanes["reproducible"] = lane(reproducible_lane)
    digest_after = source_digest(PKG)
    if digest_after != digest_before:
        lanes["tree_stable"] = {"status": "FAIL", "reason": "the CI run modified the source tree"}
    else:
        lanes["tree_stable"] = {"status": "PASS"}
    ev = {"schema": "inv53.ci/1", "run_id": "ci-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
          "source_digest": digest_before,
          "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                          "platform": platform.platform()},
          "lanes": lanes, "tests": tests, "perf_gate": perf_gate, "bench": bench_result}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(ev, indent=1, sort_keys=True) + "\n")
    summary = {k: v["status"] for k, v in lanes.items()}
    sys.stdout.write(json.dumps({"run_id": ev["run_id"], "lanes": summary, "tests": len(tests)}, indent=1) + "\n")
    return 0 if all(s == "PASS" for s in summary.values()) else (3 if "FAIL" not in summary.values() else 1)


if __name__ == "__main__":
    raise SystemExit(main())
