"""Run every INV-07 5.0.0 verification stage and print a summary.

    python -B inv07_gitops_transition_layer/components/run_all.py [--quick]

Stages: v4.2.0 reference-model tests (normal and -O), overlay test suite via the
checklist engine (writes evidence/), lint, SBOM, dashboards, API docs, doc check,
regression gate against the recorded baseline, platform report, MANIFEST.
Exit 0 = every stage passed; 3 = INCOMPLETE (stages passed, checklist has open
items -- the expected result); 1 = a stage failed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))
sys.dont_write_bytecode = True


def main() -> int:
    from inv07_gitops_transition_layer.components.checklist import engine
    from inv07_gitops_transition_layer.components.tools import gates, master
    stages = {}
    for opt in ([], ["-O"]):
        p = subprocess.run([sys.executable, "-B", *opt, os.path.join(PKG, "tests", "test_gitops_model.py")],
                           capture_output=True, text=True)
        stages["v4_reference_model" + ("_O" if opt else "")] = p.returncode == 0
    master.main()
    gates.dashboards()
    gates.api_docs()
    stages["lint"] = gates.lint()["passed"]
    gates.sbom()
    stages["doc_check"] = not gates.doc_check()
    base = os.path.join(HERE, "evidence", "perf_baseline.json")
    if os.path.exists(base) and "--quick" not in sys.argv:
        from inv07_gitops_transition_layer.components.tools import bench
        with open(base, encoding="utf-8") as fh:
            rc, fails = gates.regression(json.load(fh), bench.main(None, quick=True))
        stages["regression_gate"] = rc == 0
        gates._write("REGRESSION_GATE.json", {"schema": "INV07-REGRESSION/1", "failures": fails, "passed": rc == 0,
                                              "thresholds": gates.THRESHOLDS, "thresholds_status": "PROPOSED"})
    gates.platform_report()
    doc = engine.build()
    tr = doc["test_run"]
    stages["overlay_tests"] = not tr["failed"]
    gates.manifest()
    print(json.dumps({"stages": stages, "tests": {"ran": tr["ran"], "passed": tr["passed"],
                                                   "not_run": len(tr["not_run"]), "failed": len(tr["failed"])},
                      "checks": doc["summary"], "certification": doc["production_certification"]}, indent=1))
    if not all(stages.values()):
        return 1
    return 3 if doc["summary"]["VERIFYING"] != doc["checks"] else 0


if __name__ == "__main__":
    sys.exit(main())
