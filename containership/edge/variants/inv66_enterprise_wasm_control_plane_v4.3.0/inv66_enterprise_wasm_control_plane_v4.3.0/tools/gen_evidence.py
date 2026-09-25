#!/usr/bin/env python3
"""Generate governance/ACCEPTANCE_EVIDENCE.json (MC-060): machine-readable, digest-bound evidence.

Runs the full unit/integration suite (normal and -O), repository checks and the SBOM licence
gate; reads perf/results.json and the latest review; binds every artifact and the RTM by SHA-256.
Status vocabulary: PASS, FAIL, WAIVED, NOT_APPLICABLE, BLOCKED.  If INV66_EVIDENCE_KEY (hex) is set,
the bundle is HMAC-sealed (the CI release job additionally attests it with build provenance).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import io
import json
import os
import pathlib
import platform
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS = ROOT / "inv66_enterprise_wasm_control_plane" / "tests"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_suite(optimize: bool) -> dict:
    cmd = [sys.executable] + (["-O"] if optimize else []) + [str(ROOT / "tools/run_tests.py")]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=900)
    data = json.loads(p.stdout.strip().splitlines()[-1])
    cases = data["cases"]
    return {"command": "python " + ("-O " if optimize else "") + "tools/run_tests.py", "returncode": p.returncode if data["ok"] else 1,
            "tests": len(cases), "passed": sum(c["outcome"] == "ok" for c in cases),
            "skipped": [c for c in cases if c["outcome"].startswith("skipped")],
            "failed": [c for c in cases if c["outcome"] in ("FAIL", "ERROR")],
            "log_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(), "cases": cases}


def main() -> int:
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    suite = run_suite(False)
    suite_o = run_suite(True)
    checks = {}
    for name, script in (("sbom_licence_gate", "tools/sbom.py"),):
        p = subprocess.run([sys.executable, str(ROOT / script)], capture_output=True, text=True, cwd=ROOT)
        checks[name] = {"returncode": p.returncode, "output": p.stdout.strip()[-2000:]}
    perf = json.loads((ROOT / "perf/results.json").read_text())
    rtm_p = ROOT / "governance/RTM.json"
    rtm = json.loads(rtm_p.read_text())
    status_p = ROOT / "governance/CHECKLIST_STATUS.json"
    status = json.loads(status_p.read_text())
    reviews = sorted((ROOT / "governance/reviews").glob("*.json"))
    ctl_map = {"PASS_LOCAL": "PASS", "WAIVED_PARTIAL": "WAIVED", "NOT_APPLICABLE": "NOT_APPLICABLE"}
    tests_ok = suite["returncode"] == 0 and suite_o["returncode"] == 0
    controls = [{"id": c["id"], "status": ctl_map[c["status"]] if tests_ok else "FAIL", "basis": c["basis"],
                 "waivers": c["waivers"], "evidence": ["test-run:unittest", "test-run:unittest-O", "perf:bench"],
                 "pk_core_conformance": "BLOCKED (W-003)"} for c in rtm["controls"]]
    artifacts = {}
    for rel in ["MASTER.md", "docs/REQUIREMENTS.md", "governance/RTM.json", "governance/WAIVERS.json",
                "governance/CHECKLIST_STATUS.json", "governance/SBOM.cdx.json", "perf/results.json", "perf/thresholds.json",
                "inv66_enterprise_wasm_control_plane/service.py", "inv66_enterprise_wasm_control_plane/store.py"]:
        artifacts[rel] = sha(ROOT / rel)
    body = {
        "schema": "PK_ECP_ACCEPTANCE/1", "element": "INV-66",
        "version": (ROOT / "inv66_enterprise_wasm_control_plane/VERSION").read_text().strip(), "generated": ts,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(),
                        "kind": "clean cloud container (local run; not hosted CI — W-010)"},
        "owner": "service owner (pending, W-001)", "reviewer": None,
        "test_runs": {"unittest": {k: v for k, v in suite.items() if k != "cases"},
                      "unittest-O": {k: v for k, v in suite_o.items() if k != "cases"}},
        "test_cases": suite["cases"],
        "performance": {"gate": perf["gate"], "admission_latency_ms": perf["admission_latency_ms"],
                        "throughput_per_s": perf["throughput_per_s"], "env": perf["env"]},
        "checks": checks,
        "review": {"file": reviews[-1].name, "sha256": sha(reviews[-1])} if reviews else None,
        "controls": controls,
        "components": [{"id": r["id"], "disposition": r["disposition"], "counts": r["counts"], "waivers": r["waivers"]} for r in rtm["components"]],
        "checklist_totals": status["totals"], "artifacts_sha256": artifacts,
    }
    key = os.environ.get("INV66_EVIDENCE_KEY")
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["bundle_sha256"] = hashlib.sha256(canon).hexdigest()
    body["seal"] = ({"alg": "HMAC-SHA256", "mac": hmac.new(bytes.fromhex(key), canon, hashlib.sha256).hexdigest()}
                    if key else {"alg": None, "note": "unsealed local run; CI release job attests the bundle"})
    (ROOT / "governance/ACCEPTANCE_EVIDENCE.json").write_text(json.dumps(body, indent=2) + "\n")
    print(json.dumps({"tests": suite["tests"], "passed": suite["passed"], "skipped": len(suite["skipped"]),
                      "failed": len(suite["failed"]), "O_passed": suite_o["passed"], "bundle": body["bundle_sha256"][:16]}))
    return 0 if tests_ok else 1


if __name__ == "__main__":
    sys.exit(main())
