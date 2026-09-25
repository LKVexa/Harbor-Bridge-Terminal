"""Run the full dependency-free test suite and emit machine-readable evidence.

Usage: python tests/run_all.py [--evidence PATH]
"""
from __future__ import annotations
import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
from inv38_kernel_bypass_transport.tests.harness import run_all  # noqa

MODULES = [
 "inv38_kernel_bypass_transport.tests.test_outcomes",
 "inv38_kernel_bypass_transport.tests.test_lifecycle",
 "inv38_kernel_bypass_transport.tests.test_precedence",
 "inv38_kernel_bypass_transport.tests.test_rtm",
 "inv38_kernel_bypass_transport.tests.test_schemas_golden",
 "inv38_kernel_bypass_transport.tests.test_authz",
 "inv38_kernel_bypass_transport.tests.test_negotiation",
 "inv38_kernel_bypass_transport.tests.test_config_txn",
 "inv38_kernel_bypass_transport.tests.test_config_provenance",
 "inv38_kernel_bypass_transport.tests.test_config_layout",
 "inv38_kernel_bypass_transport.tests.test_privilege",
 "inv38_kernel_bypass_transport.tests.test_supply_chain",
 "inv38_kernel_bypass_transport.tests.test_failsafe",
 "inv38_kernel_bypass_transport.tests.test_audit_log",
 "inv38_kernel_bypass_transport.tests.test_retry",
 "inv38_kernel_bypass_transport.tests.test_recovery",
 "inv38_kernel_bypass_transport.tests.test_fencing",
 "inv38_kernel_bypass_transport.tests.test_health_stall",
 "inv38_kernel_bypass_transport.tests.test_status",
 "inv38_kernel_bypass_transport.tests.test_logging",
 "inv38_kernel_bypass_transport.tests.test_tracing",
 "inv38_kernel_bypass_transport.tests.test_decisions",
 "inv38_kernel_bypass_transport.tests.test_telemetry_policy",
 "inv38_kernel_bypass_transport.tests.test_perf_gate",
 "inv38_kernel_bypass_transport.tests.test_release_gate",
 "inv38_kernel_bypass_transport.tests.test_governance_checks",
 "inv38_kernel_bypass_transport.tests.test_deployment_contexts",
 "inv38_kernel_bypass_transport.tests.test_version_support",
 "inv38_kernel_bypass_transport.tests.test_severity",
 "inv38_kernel_bypass_transport.tests.test_alerts",
 "inv38_kernel_bypass_transport.tests.test_artifacts_present",
 "inv38_kernel_bypass_transport.tests.compatibility.test_reference_row",
 "inv38_kernel_bypass_transport.tests.fuzz.fuzz_transport",
 "inv38_kernel_bypass_transport.tests.soak.test_model_soak",
 "inv38_kernel_bypass_transport.tests.disaster.test_model_faults",
 "inv38_kernel_bypass_transport.tests.recovery.test_reconstruction",
]

def main() -> int:
    summary = run_all(MODULES)
    summary["generated_at"] = time.time()
    summary["suite"] = "inv38-remediation"
    out = ROOT + "/release/attestations/test-results.json"
    if "--evidence" in sys.argv:
        out = sys.argv[sys.argv.index("--evidence")+1]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f: json.dump(summary, f, indent=2)
    print(f"TESTS: {summary['passed']}/{summary['total']} passed, {summary['failed']} failed")
    for r in summary["results"]:
        if r["status"] != "PASS":
            print(f"  {r['status']} {r['module']}::{r['test']} - {r.get('error','')}")
    return 0 if summary["failed"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
