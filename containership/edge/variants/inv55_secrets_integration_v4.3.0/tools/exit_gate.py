#!/usr/bin/env python3
"""Formal production exit gate (checklist #99).

Inputs: evidence/traceability.json, evidence/release_evidence.json, docs/governance/waiver-register.md
Verdict (written to evidence/exit_gate.json):
  NO_GO            any failing/erroring test; secret-scan finding; missing artifact; any MANDATORY
                   suite skipped; any P0 component not IMPLEMENTED
  CONDITIONAL_GO   all P0 IMPLEMENTED, but P1/P2 gaps remain -> conditions listed, need owner acceptance
  GO               everything IMPLEMENTED, no skips, and owner approvals recorded (never produced by
                   tooling alone: approvals are an owner act)
A skipped mandatory test is never counted as a pass.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANDATORY_SUITES = ("test_vault_real", "test_component", "test_schemas_fixtures")


def evaluate(trace: dict, ev: dict) -> dict:
    reasons, conditions = [], []
    counts = ev["tests"]["counts"]
    if counts.get("fail") or counts.get("error"):
        reasons.append(f"tests failing: {counts}")
    if ev["secret_scan"]["exit"] != 0:
        reasons.append("secret-scan findings")
    if trace["missing_artifacts"]:
        reasons.append(f"missing artifacts: {trace['missing_artifacts']}")
    skipped = [t for t in ev["tests"]["results"] if t["result"] == "skip"
               and t["test"].split(".")[0] in MANDATORY_SUITES]
    for t in skipped:
        reasons.append(f"mandatory test skipped: {t['test']} ({t['detail']})")
    for c in trace["components"]:
        if c["status"] != "IMPLEMENTED":
            line = f"#{c['id']} {c['title']} [{c['priority']} {c['status']}]: {c['residual']}"
            (reasons if c["priority"] == "P0" else conditions).append(line)
    verdict = "NO_GO" if reasons else ("CONDITIONAL_GO" if conditions else "GO_PENDING_OWNER_APPROVAL")
    return {"format": "inv55-exit-gate/1", "component": "INV-55", "version": ev["version"],
            "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_tree_sha256": ev["source_tree_sha256"], "verdict": verdict,
            "blocking_reasons": reasons, "conditions": conditions,
            "approvals": {"engineering": "PENDING", "security": "PENDING", "operations": "PENDING"}}


def main() -> int:
    trace = json.loads((ROOT / "evidence" / "traceability.json").read_text())
    ev = json.loads((ROOT / "evidence" / "release_evidence.json").read_text())
    out = evaluate(trace, ev)
    (ROOT / "evidence" / "exit_gate.json").write_text(json.dumps(out, indent=1))
    print(f"verdict: {out['verdict']}  blocking={len(out['blocking_reasons'])}  conditions={len(out['conditions'])}")
    return 0 if out["verdict"] != "NO_GO" else 2


if __name__ == "__main__":
    sys.exit(main())
