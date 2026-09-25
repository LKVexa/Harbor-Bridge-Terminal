"""Run every evidence producer, write evidence/*.json + logs, seal a manifest, then run the exit gate.

``python -m inv26_microvm_snapshotting.tools.run_evidence [--quick]``
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parent
EV = PKG / "evidence"
M = "inv26_microvm_snapshotting"


def sh(name: str, args: list[str], timeout: int = 1800, env=None) -> subprocess.CompletedProcess:
    t0 = time.time()
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env or {})))
    (EV / "logs").mkdir(parents=True, exist_ok=True)
    (EV / "logs" / f"{name}.log").write_text(f"$ python {' '.join(args)}\n# rc={r.returncode} "
                                             f"seconds={time.time() - t0:.1f}\n{r.stdout}\n{r.stderr}")
    return r


def unit(name: str, optimize: bool) -> dict:
    args = (["-O"] if optimize else []) + ["-m", "unittest", "discover", "-s", f"{M}/tests", "-t", ".", "-v"]
    r = sh(name, args)
    txt = r.stderr
    ran = int(re.search(r"Ran (\d+) tests", txt).group(1)) if re.search(r"Ran (\d+) tests", txt) else 0
    skipped = int(m.group(1)) if (m := re.search(r"skipped=(\d+)", txt)) else 0
    failures = int(m.group(1)) if (m := re.search(r"failures=(\d+)", txt)) else 0
    errors = int(m.group(1)) if (m := re.search(r"errors=(\d+)", txt)) else 0
    skipped_tests = re.findall(r"^(\w+) \(([\w.]+)\).*skipped '(.*)'$", txt, re.M)
    return {"schema": "PK_SNAPSHOT_TESTS/1", "optimize": optimize, "ran": ran, "passed": ran - skipped - failures - errors,
            "skipped": skipped, "failures": failures, "errors": errors,
            "skipped_detail": [{"test": f"{c}.{t}", "reason": why} for t, c, why in skipped_tests],
            "python": sys.version.split()[0], "result": "PASS" if r.returncode == 0 else "FAIL"}


def jdump(name: str, obj) -> None:
    (EV / name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    if EV.exists():
        shutil.rmtree(EV)
    EV.mkdir()
    steps = {}
    jdump("TESTS.json", unit("tests", False))
    jdump("TESTS_O.json", unit("tests_O", True))
    steps["fuzz"] = sh("fuzz", ["-m", f"{M}.tools.fuzz", "--iterations", "900" if a.quick else "6000", "--seed", "26",
                                "--out", str(EV / "FUZZ.json")])
    steps["faults"] = sh("faults", ["-m", f"{M}.tools.faults", "--out", str(EV / "FAULTS.json")])
    steps["drills"] = sh("drills", ["-m", f"{M}.tools.drills", "--out", str(EV / "DRILLS.json")])
    steps["bench"] = sh("bench", ["-m", f"{M}.tools.bench", "--profile", "quick", "--out", str(EV / "BENCH.json")])
    steps["perf_gate"] = sh("perf_gate", ["-m", f"{M}.tools.bench", "--compare", str(PKG / "bench" / "baseline.json"),
                                          str(EV / "BENCH.json"), "--out", str(EV / "PERF_GATE.json")])
    if (PKG / "bench" / "pre_optimization.json").exists():
        shutil.copy(PKG / "bench" / "pre_optimization.json", EV / "BENCH_PRE_OPT.json")
    steps["soak"] = sh("soak", ["-m", f"{M}.tools.soak", "--seconds", "45" if a.quick else "120",
                                "--out", str(EV / "SOAK.json")])
    r = sh("stress", ["-m", "unittest", f"{M}.tests.test_concurrency", "-v"])
    jdump("STRESS.json", {"schema": "PK_SNAPSHOT_STRESS/1", "suite": "tests/test_concurrency.py (threads + 4-process CAS)",
                          "log": "logs/stress.log", "result": "PASS" if r.returncode == 0 else "FAIL"})
    r = sh("integration", ["-m", "unittest", f"{M}.tests.test_adapters", "-v"])
    jdump("INTEGRATION.json", {"schema": "PK_SNAPSHOT_INTEGRATION/1", "kind": "protocol fakes over real Unix sockets",
                               "adapters": ["firecracker", "cloud-hypervisor", "vsock entropy agent"],
                               "real_vmm": False, "log": "logs/integration.log",
                               "result": "PASS" if r.returncode == 0 else "FAIL"})
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in
              [*(PKG / "schemas").glob("*.json"), PKG / "ERRORS.json", *(PKG / "ops").glob("*.json"),
               *(PKG / "examples").glob("*.json"), PKG / "tests/fixtures/conformance/cases.json"]}
    r = sh("schemas", ["-m", f"{M}.tools.gen_artifacts"])
    drift = [str(p.relative_to(PKG)) for p, h in before.items() if hashlib.sha256(p.read_bytes()).hexdigest() != h]
    jdump("SCHEMAS.json", {"schema": "PK_SNAPSHOT_SCHEMAS_CHECK/1", "files": len(before), "drift": drift,
                           "result": "PASS" if r.returncode == 0 and not drift else "FAIL"})
    steps["secrets"] = sh("secret_scan", ["-m", f"{M}.tools.secret_scan", "--out", str(EV / "SECRET_SCAN.json")])
    r = sh("governance", ["-m", f"{M}.tools.governance_check"])
    (EV / "GOVERNANCE.json").write_text(r.stdout)
    steps["rtm"] = sh("rtm", ["-m", f"{M}.tools.rtm", "--check", "--write", "--out", str(EV / "RTM.json")])
    dist = ROOT / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    steps["release"] = sh("release", ["-m", f"{M}.tools.release", "all", "--dist", str(dist),
                                      "--out", str(EV / "RELEASE.json")])
    rel = json.loads((EV / "RELEASE.json").read_text())
    jdump("INSTALL.json", dict(rel.get("install", {}), schema="PK_SNAPSHOT_INSTALL/1"))
    if (dist / "sbom.cdx.json").exists():
        shutil.copy(dist / "sbom.cdx.json", EV / "sbom.cdx.json")
    steps["preflight"] = sh("preflight", ["-m", f"{M}.tools.preflight", "--profile", "reference", "--json",
                                          "--out", str(EV / "PREFLIGHT.json")])
    smoke_root = Path(os.environ.get("TMPDIR", "/tmp")) / f"inv26-smoke-{os.getpid()}"
    steps["smoke"] = sh("smoke", ["-m", f"{M}.tools.smoke", "--root", str(smoke_root), "--out", str(EV / "SMOKE.json")])
    ledger = smoke_root / "smoke" / "audit.jsonl"
    r = sh("audit_verify", ["-m", f"{M}.audit", "verify", str(ledger), "--key-env", "INV26_SMOKE_AUDIT_KEY"],
           env={"INV26_SMOKE_AUDIT_KEY": (b"k" * 32).hex()})
    try:
        av = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        av = {"result": "FAIL", "error": r.stderr[-300:]}
    jdump("AUDIT_VERIFY.json", av)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EV.glob("*.json"))
             if p.name not in ("EXIT_GATE.json", "EVIDENCE_MANIFEST.json")}
    src = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PKG, capture_output=True, text=True).stdout.strip()
    jdump("EVIDENCE_MANIFEST.json", {"schema": "PK_SNAPSHOT_EVIDENCE_MANIFEST/1", "source_revision": src or None,
                                     "artifacts": rel.get("build", {}).get("artifacts"), "files": files})
    g = sh("gate", ["-m", f"{M}.tools.gate", "--selftest"])
    summary = {k: v.returncode for k, v in steps.items()}
    print(json.dumps({"steps_rc": summary, "gate": g.stdout.strip()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
