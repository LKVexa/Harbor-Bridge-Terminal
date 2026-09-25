#!/usr/bin/env python3
"""MC-004 - requirements traceability matrix generator/validator.

Maps all 100 CHECKLIST.json requirements to evidence (``file`` or
``file::symbol``) and a disposition.  ``--check`` fails (exit 6) if any
requirement is unmapped, any evidence path/symbol is missing, or a waived item
lacks a live waiver in WAIVERS.json.  Output: TRACEABILITY.json.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
T = "tests/test_hardening_v43.py"
I = "tests/test_integration.py"
R = "tests/test_descriptors.py"
M = "met"
X = "met-pending-external-evidence"
W = "waived"
NA = "not-applicable"

MAP = {
 1: (M, ["contract.py::responsibility", "README.md"]),
 2: (M, ["contract.py::not_owns", "README.md"]),
 3: (M, ["contract.py::Dependency", "SPEC_MANIFEST.json::adjacent_layers"]),
 4: (M, ["contract.py::source_of_truth"]),
 5: (M, ["contract.py::assumptions", "NFR.md::Deployment contexts"]),
 6: (M, ["contract.py::boundaries"]),
 7: (M, ["contract.py::optional"]),
 8: (M, ["contract.py::non_goals", "NFR.md::Unsupported"]),
 9: (W, ["OWNERS.yaml::accountable_owner"], "W-003"),
 10: (M, ["docs/ADR-0001-authenticated-descriptors.md", "docs/ADR-0002-delegation-by-reissuance.md", "docs/ADR-0003-transport-profile.md", "docs/ADR-0004-observability.md"]),
 11: (W, ["NFR.md::SHALL requirements"], "W-002"),
 12: (M, ["NFR.md::Deployment contexts"]),
 13: (M, ["NFR.md::Quantitative", "PERF_THRESHOLDS.json"]),
 14: (M, ["outcomes.py::TAXONOMY", f"{T}::OutcomeTaxonomyTest"]),
 15: (M, ["OPERATIONS.md::Lifecycle", "descriptors.py::destroy"]),
 16: (M, ["COMPATIBILITY.md", "SPEC_MANIFEST.json::protocols"]),
 17: (M, ["descriptors.py::TABLE_LIMIT", "descriptors.py::SESSION_ALLOCATION_LIMIT"]),
 18: (M, ["NFR.md::Disconnected"]),
 19: (M, ["NFR.md::Precedence"]),
 20: (M, ["TRACEABILITY.json", "tools/traceability.py"]),
 21: (M, ["SPEC_MANIFEST.json::protocols", "wit/inv42-descriptor.wit"]),
 22: (M, ["schemas/PK_DESCRIPTOR_v2.schema.json", "schemas/PK_DESCRIPTOR_EVENT_v1.schema.json", f"{I}::test_outputs_conform_to_schemas"]),
 23: (M, ["descriptors.py::_authenticate_locked", "transport.py::assert_secure"]),
 24: (M, ["descriptors.py::resolve", "delegation.py::deny_all"]),
 25: (M, ["outcomes.py::RETRY_POLICY", "delegation.py::txn_id"]),
 26: (M, ["descriptors.py::as_dict", "outcomes.py::classify"]),
 27: (M, ["COMPATIBILITY.md"]),
 28: (M, ["descriptors.py::MAX_RESOURCE_TYPE_BYTES", "transport.py::MAX_FRAME", "adapters.py::MAX_ABI_BYTES"]),
 29: (M, ["tests/fixtures/fuzz_corpus.json", "schemas/PK_DESCRIPTOR_v2.schema.json"]),
 30: (X, [f"{I}::AdjacentLayerTest", "adapters.py"], "real sibling INV-41/INV-13/PLN-03 builds not in this archive"),
 31: (W, ["SPEC_MANIFEST.json::dependencies"], "W-001"),
 32: (M, ["NFR.md::Configuration"]),
 33: (M, ["component.py::Secure defaults", "NFR.md::Configuration"]),
 34: (NA, ["NFR.md::Configuration"]),
 35: (NA, ["NFR.md::Configuration"]),
 36: (NA, ["NFR.md::Configuration"]),
 37: (NA, ["NFR.md::Configuration"]),
 38: (M, ["ROLLOUT.md", "tools/rollout.py"]),
 39: (M, ["audit.py::FORBIDDEN_FIELDS", "telemetry.py::redact", f"{T}::test_chain_verifies_and_contains_no_bearer_material"]),
 40: (X, ["tools/certify.py", "pyproject.toml"], "pk_core must be pinned (W-001)"),
 41: (M, ["THREAT_MODEL.md"]),
 42: (M, ["THREAT_MODEL.md::Least privilege"]),
 43: (M, ["THREAT_MODEL.md::Ambient authority"]),
 44: (M, ["transport.py::assert_secure", "tools/release.py::cmd_verify"]),
 45: (X, ["tools/release.py", "RELEASE.md"], "production signing key in KMS/HSM not provisioned (W-004)"),
 46: (M, ["descriptors.py::ForeignDescriptor", f"{I}::test_process_transfer_confers_no_authority"]),
 47: (X, ["transport.py", "KEY_MANAGEMENT.md"], "no at-rest state; transport requires deployment PKI"),
 48: (M, ["descriptors.py::KeyUnavailable", "NFR.md::External services", f"{T}::KeyProviderTest"]),
 49: (M, ["audit.py::AuditLog", f"{T}::AuditTest"]),
 50: (M, [f"{T}::AdversarialTest", f"{T}::FuzzTest"]),
 51: (M, ["THREAT_MODEL.md::Failure enumeration"]),
 52: (M, ["telemetry.py::health", "telemetry.py::STALL_SECONDS"]),
 53: (M, ["outcomes.py::RETRY_POLICY"]),
 54: (M, ["descriptors.py::TableFull", f"{T}::test_sustained_exhaustion_bounded"]),
 55: (NA, ["NFR.md::Failover"]),
 56: (M, ["descriptors.py::_emit", f"{T}::test_observer_failure_never_changes_decision"]),
 57: (M, ["OPERATIONS.md::Lifecycle", f"{T}::test_restart_does_not_restore_authority"]),
 58: (M, ["descriptors.py::ForkedTable", "delegation.py::txn_id"]),
 59: (M, ["descriptors.py::emergency_disable", f"{T}::EmergencyDisableTest"]),
 60: (M, [f"{T}::FaultInjectionTest"]),
 61: (X, ["tools/bench.py", "PERF_THRESHOLDS.json::baseline"], "baseline is one reference host"),
 62: (M, ["PERF_THRESHOLDS.json::latency_us"]),
 63: (M, ["tools/bench.py::burst", "tools/bench.py::soak"]),
 64: (M, ["tools/bench.py::fleet"]),
 65: (M, ["NFR.md::Efficiency"]),
 66: (NA, ["NFR.md::Efficiency"]),
 67: (M, ["descriptors.py::TABLE_LIMIT", "delegation.py::max_txns", "transport.py::MAX_FRAME"]),
 68: (NA, ["NFR.md::Edge power"]),
 69: (M, ["telemetry.py::inv42_table_saturation_ratio", "alerts/inv42_alerts.yml"]),
 70: (M, ["tools/bench.py::violations", ".github/workflows/ci.yml"]),
 71: (M, ["telemetry.py::health", "descriptors.py::status"]),
 72: (M, ["telemetry.py::Metrics"]),
 73: (M, ["telemetry.py::StructuredLogger"]),
 74: (M, ["telemetry.py::parse_traceparent", "telemetry.py::with_trace"]),
 75: (M, ["telemetry.py::redact", "descriptors.py::fingerprint"]),
 76: (M, ["descriptors.py::_emit", "audit.py::AuditLog"]),
 77: (M, ["telemetry.py::explain"]),
 78: (X, ["telemetry.py::release"], "live infrastructure graph is a platform service"),
 79: (M, ["TELEMETRY_POLICY.md"]),
 80: (M, ["dashboards/inv42_dashboard.json", "alerts/inv42_alerts.yml"]),
 81: (M, [f"{R}::DescriptorRuntimeTest"]),
 82: (M, [f"{I}::test_outputs_conform_to_schemas", f"{R}::test_wire_round_trip"]),
 83: (X, [f"{I}::AdjacentLayerTest"], "real sibling layers not bundled"),
 84: (X, [".github/workflows/ci.yml::matrix"], "matrix defined; CI run evidence required"),
 85: (M, [f"{T}::FuzzTest"]),
 86: (M, [f"{T}::ConcurrencyTest"]),
 87: (M, ["THREAT_MODEL.md", f"{T}::AdversarialTest"]),
 88: (M, ["tools/bench.py"]),
 89: (M, [f"{I}::test_degraded_control_plane", f"{T}::FaultInjectionTest"]),
 90: (M, ["tools/exit_gate.py", "tools/certify.py"]),
 91: (M, ["SLO.md"]),
 92: (M, ["ROLLOUT.md", "tools/rollout.py"]),
 93: (M, ["COMPATIBILITY.md", "VULNERABILITY_POLICY.md::Support windows"]),
 94: (M, ["VULNERABILITY_POLICY.md"]),
 95: (M, ["OPERATIONS.md::Lifecycle"]),
 96: (M, ["README.md::Day 0", "OPERATIONS.md"]),
 97: (M, ["INCIDENT_RUNBOOK.md"]),
 98: (M, ["REVIEWS.json", "tools/review_due.py", ".github/workflows/review.yml"]),
 99: (M, ["WAIVERS.json"]),
 100: (M, ["tools/exit_gate.py"]),
}


def evidence_ok(ref: str) -> bool:
    path, _, sym = ref.partition("::")
    p = PKG / path
    if not p.exists():
        return False
    return not sym or sym.split(" ")[0] in p.read_text(errors="replace") or sym in p.read_text(errors="replace")


def main():
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    waivers = {w["id"]: w for w in json.loads((PKG / "WAIVERS.json").read_text())["waivers"]}
    today = datetime.date.today().isoformat()
    rows, problems = [], []
    for it in items:
        n = it["ordinal"]
        if n not in MAP:
            problems.append(f"{it['check_id']} unmapped")
            continue
        status, ev, *extra = MAP[n]
        note = extra[0] if extra else None
        bad = [e for e in ev if not evidence_ok(e)]
        if bad:
            problems.append(f"{it['check_id']} missing evidence {bad}")
        if status == W:
            w = waivers.get(note)
            if not w or w["expires"] < today:
                problems.append(f"{it['check_id']} waiver {note} missing/expired")
        rows.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                     "status": status, "evidence": ev, "note": note})
    summary = {}
    for r in rows:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    doc = {"schema": "INV42_TRACEABILITY/1", "version": (PKG / "VERSION").read_text().strip(),
           "summary": summary, "rows": rows}
    if "--check" not in sys.argv:
        (PKG / "TRACEABILITY.json").write_text(json.dumps(doc, indent=1) + "\n")
    for p in problems:
        print("TRACE FAIL:", p, file=sys.stderr)
    print(json.dumps(summary))
    return 6 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
