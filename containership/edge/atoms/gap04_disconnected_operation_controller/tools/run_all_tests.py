"""Run every GAP-04 suite and record machine-readable evidence (evidence/test_results.json).
Also re-runs the reference controller suite under ``python -O`` (production optimization, C31-003)."""
import datetime as dt, json, os, platform, re, subprocess, sys, time, uuid
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
SUITES = ["test_controller.py", "test_p0_lease_policy.py", "test_p0_durability.py", "test_p0_reconcile_adapters.py",
          "test_crash_recovery.py", "test_p1_operations.py", "test_p1_resilience_suites.py",
          "test_p1_contracts_integration.py", "test_p2_governance.py", "test_component.py"]


def run(args):
    t = time.time()
    p = subprocess.run([sys.executable, *args, "-v"], cwd=PKG / "tests", capture_output=True, text=True, timeout=1800)
    err = p.stderr
    tests = re.findall(r"^(test_\S+) \((\S+)\)(?:\n.*?)? \.\.\. (ok|FAIL|ERROR|skipped.*)$", err, re.M)
    m = re.search(r"Ran (\d+) tests", err)
    summ = re.search(r"^(OK|FAILED)(?: \((.*)\))?$", err, re.M)
    kv = dict(x.split("=") for x in (summ.group(2) or "").split(", ") if "=" in x) if summ else {}
    return {"suite": " ".join(args), "rc": p.returncode, "ran": int(m.group(1)) if m else 0, "seconds": round(time.time() - t, 1),
            "failures": int(kv.get("failures", 0)) + (0 if summ else 1), "errors": int(kv.get("errors", 0)),
            "skipped": int(kv.get("skipped", 0)),
            "tests": [{"id": f"{c}.{n}", "result": r.split()[0]} for n, c, r in tests]}


if __name__ == "__main__":
    only_pre = "--pre-governance" in sys.argv
    res = []
    for s in SUITES:
        if only_pre and s == "test_p2_governance.py":
            continue
        res.append(run([s]))
    res.append(run(["-O", "test_controller.py"]))
    allt = [t for r in res for t in r["tests"]]
    out = {"schema": "PK_GAP04_TEST_RESULTS/1", "run_id": "local-" + uuid.uuid4().hex[:12], "ci_run_id": None,
           "date": dt.date.today().isoformat(), "host": {"python": platform.python_version(), "platform": platform.platform()},
           "ran": sum(r["ran"] for r in res), "failed": sum(r["failures"] for r in res), "errors": sum(r["errors"] for r in res),
           "skipped": sum(r["skipped"] for r in res), "suites": res,
           "note": "local run; not release CI (waiver W-007). test_component.py requires pk_core (W-003)."}
    (PKG / "evidence" / "test_results.json").write_text(json.dumps(out, indent=1))
    out["passed"] = out["ran"] - out["failed"] - out["errors"] - out["skipped"]
    (PKG / "evidence" / "test_results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("run_id", "ran", "passed", "failed", "errors", "skipped")}))
    sys.exit(0 if not out["failed"] and not out["errors"] else 1)
