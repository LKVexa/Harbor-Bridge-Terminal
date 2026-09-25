"""Generate TRACEABILITY.json: C001-C100 -> requirements, artifacts, tests, status.

Status vocabulary:
  implemented  - in-repo implementation + automated test evidence
  documented   - normative document is the deliverable (policy/runbook/ADR)
  partial      - in-repo evidence exists but an external dependency/approval is open (waiver cited)
  external     - cannot be evidenced from this repository (waiver cited)

``--check`` regenerates in memory and fails if the committed file differs,
any referenced file is missing, or any referenced test does not exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
OUT = PKG / "TRACEABILITY.json"

T = "tests/"
D = "docs/"
# control -> (requirements, artifacts, tests, status, waiver)
MAP: dict[int, tuple] = {
    1: (["RQ-001"], ["README.md", D + "REQUIREMENTS.md"], [], "documented", None),
    2: (["RQ-002"], ["README.md", "contract.py"], [], "documented", None),
    3: (["RQ-002"], ["contract.py", D + "ARCHITECTURE.md"], ["test_concurrency_integration.AdjacentLayerTest"], "documented", None),
    4: (["RQ-003"], ["server.py"], ["test_security_pipeline.AdversarialSuite.test_ac01_signature_drift"], "implemented", None),
    5: (["RQ-005"], [D + "ARCHITECTURE.md", "contract.py"], [], "documented", None),
    6: (["RQ-024"], ["security.py", D + "ARCHITECTURE.md"], ["test_security_pipeline.AuthzTest"], "implemented", None),
    7: (["RQ-004"], [D + "REQUIREMENTS.md"], [], "documented", None),
    8: (["RQ-002"], [D + "ARCHITECTURE.md"], [], "documented", None),
    9: ([], ["OWNERS.md"], [], "external", "W-001"),
    10: ([], [D + "adr/ADR-0001-wrpc-architecture.md"], [], "partial", "W-001"),
    11: (["RQ-001"], ["transport.py", "server.py"], ["test_transport.TwoProcessTest"], "implemented", None),
    12: (["RQ-005"], [D + "ARCHITECTURE.md"], [], "partial", "W-010"),
    13: (["RQ-030"], [D + "REQUIREMENTS.md"], [], "documented", None),
    14: (["RQ-016"], [D + "REQUIREMENTS.md", "resilience.py"], ["test_subsystems.ResilienceTest.test_retry_classification_and_backoff"], "implemented", None),
    15: (["RQ-038"], [D + "ARCHITECTURE.md", "transport.py"], ["test_transport.FaultInjectionTest.test_graceful_drain_waits_for_inflight"], "implemented", None),
    16: (["RQ-014", "RQ-015"], ["negotiation.py", "COMPAT_MATRIX.json"], ["test_subsystems.NegotiationTest"], "implemented", None),
    17: (["RQ-034"], ["resilience.py"], ["test_subsystems.ResilienceTest.test_admission"], "implemented", None),
    18: (["RQ-039"], ["transport.py"], ["test_transport.FaultInjectionTest.test_reconnect_after_server_restart_and_ambiguous_completion"], "implemented", None),
    19: ([], [D + "REQUIREMENTS.md"], [], "documented", None),
    20: ([], ["TRACEABILITY.json", "tools/build_traceability.py"], ["test_traceability"], "implemented", None),
    21: (["RQ-010"], ["wit/kv.wit", D + "ARCHITECTURE.md"], ["test_wit_codec.WitParserTest"], "implemented", None),
    22: (["RQ-010", "RQ-011"], ["wit_model.py", "codec.py", D + "WIT_SUBSET.md"], ["test_wit_codec.CodecTest"], "implemented", None),
    23: (["RQ-020", "RQ-021"], ["security.py", "transport.py"], ["test_security_pipeline.AuthnTest", "test_transport.TlsTest"], "implemented", None),
    24: (["RQ-024"], ["security.py"], ["test_security_pipeline.AuthzTest"], "implemented", None),
    25: (["RQ-030", "RQ-031", "RQ-032", "RQ-033", "RQ-034"], ["resilience.py", "transport.py"],
         ["test_transport.LoopbackTest.test_cancellation_propagates", "test_transport.LoopbackTest.test_server_deadline"], "implemented", None),
    26: (["RQ-016"], [D + "REQUIREMENTS.md", "server.py"], ["test_wit_codec.CodecTest.test_decode_rejections"], "implemented", None),
    27: (["RQ-014"], ["negotiation.py", "COMPAT_MATRIX.json"], ["test_transport.LoopbackTest.test_version_negotiation_down_to_2_0"], "implemented", None),
    28: (["RQ-012", "RQ-013"], ["codec.py", "config.py"], ["test_wit_codec.CodecTest.test_header_checked_before_allocation"], "implemented", None),
    29: ([], ["tests/fixtures/golden.json", "tools/gen_fixtures.py"], ["test_traceability.GoldenFixtureTest"], "partial", "W-005"),
    30: ([], ["tests/test_concurrency_integration.py"], ["test_concurrency_integration.AdjacentLayerTest"], "partial", "W-006"),
    31: (["RQ-010"], ["pyproject.toml", "COMPAT_MATRIX.json"], [], "partial", "W-002"),
    32: (["RQ-041"], ["config.py", D + "STATE_INVENTORY.md"], ["test_subsystems.ConfigTest"], "implemented", None),
    33: (["RQ-040"], ["config.py", "deploy/config.example.json"], ["test_subsystems.ConfigTest.test_validate"], "implemented", None),
    34: (["RQ-040"], ["config.py"], ["test_subsystems.ConfigTest.test_validate"], "implemented", None),
    35: (["RQ-041"], ["config.py"], ["test_subsystems.ConfigTest.test_layers_provenance_activation_rollback"], "implemented", None),
    36: (["RQ-042"], ["config.py"], ["test_subsystems.ConfigTest.test_layers_provenance_activation_rollback"], "implemented", None),
    37: (["RQ-042"], ["config.py"], ["test_subsystems.ConfigTest.test_layers_provenance_activation_rollback"], "implemented", None),
    38: (["RQ-042", "RQ-038"], ["config.py", "bootstrap.sh", D + "OPERATIONS.md"], ["test_subsystems.ConfigTest.test_layers_provenance_activation_rollback"], "implemented", None),
    39: (["RQ-040"], ["config.py", "observability.py"], ["test_subsystems.ConfigTest.test_secret_resolution"], "implemented", None),
    40: (["RQ-028"], ["bootstrap.sh", "pyproject.toml", "selfcheck.py"], ["test_traceability.PackagingTest"], "implemented", None),
    41: (["RQ-023"], [D + "THREAT_MODEL.md"], ["test_security_pipeline.AdversarialSuite"], "implemented", None),
    42: (["RQ-024"], ["security.py"], ["test_security_pipeline.AuthzTest"], "implemented", None),
    43: (["RQ-025"], ["server.py"], ["test_security_pipeline.AuthnTest.test_unauthenticated_peer_never_reaches_lookup"], "implemented", None),
    44: (["RQ-021", "RQ-025"], ["security.py", "transport.py"], ["test_transport.TlsTest"], "implemented", None),
    45: (["RQ-028"], ["tools/make_release.py", "tools/verify_release.py"], ["test_traceability.PackagingTest"], "partial", "W-011"),
    46: (["RQ-024"], ["security.py", "resilience.py"], ["test_security_pipeline.AuthzTest"], "implemented", None),
    47: (["RQ-020", "RQ-022"], ["transport.py", "security.py", D + "adr/ADR-0004-crypto-and-keys.md"], ["test_transport.TlsTest"], "partial", "W-004"),
    48: (["RQ-027"], [D + "adr/ADR-0004-crypto-and-keys.md"], ["test_security_pipeline.AuthnTest.test_revoked_and_expired_keys"], "implemented", None),
    49: (["RQ-026"], ["security.py"], ["test_security_pipeline.AuditTest"], "implemented", None),
    50: (["RQ-015", "RQ-023"], [D + "THREAT_MODEL.md"], ["test_security_pipeline.AdversarialSuite", "test_security_pipeline.ReplayTest"], "partial", "W-008"),
    51: ([], [D + "ARCHITECTURE.md"], [], "documented", None),
    52: (["RQ-043"], ["observability.py"], ["test_subsystems.ObservabilityTest.test_health"], "implemented", None),
    53: (["RQ-032"], ["resilience.py", "transport.py"], ["test_subsystems.ResilienceTest.test_retry_classification_and_backoff"], "implemented", None),
    54: (["RQ-034", "RQ-035"], ["resilience.py"], ["test_subsystems.ResilienceTest.test_breaker_state_machine", "test_transport.FaultInjectionTest.test_overload_is_shed_with_retryable_status"], "implemented", None),
    55: (["RQ-036"], ["state.py", D + "adr/ADR-0003-ownership-authority.md"], ["test_subsystems.OwnershipStateTest"], "partial", "W-007"),
    56: (["RQ-043"], ["observability.py"], ["test_subsystems.ObservabilityTest.test_health"], "implemented", None),
    57: (["RQ-033"], ["state.py", D + "STATE_INVENTORY.md"], ["test_subsystems.OwnershipStateTest.test_restart_preserves_idempotency_disable_and_epoch"], "implemented", None),
    58: (["RQ-033", "RQ-036"], ["state.py", "resilience.py"], ["test_concurrency_integration.ConcurrencyTest.test_idempotent_duplicates_race_to_single_execution"], "partial", "W-007"),
    59: (["RQ-037"], ["server.py"], ["test_security_pipeline.AdversarialSuite.test_ac08_emergency_disable"], "implemented", None),
    60: ([], ["tests/test_transport.py"], ["test_transport.FaultInjectionTest"], "implemented", None),
    61: ([], ["bench/bench.py", "evidence/bench_results.json"], [], "implemented", None),
    62: ([], ["tools/perf_gate.py", "bench/thresholds.json"], [], "implemented", None),
    63: ([], ["bench/bench.py"], ["test_transport.FaultInjectionTest.test_overload_is_shed_with_retryable_status"], "partial", "W-010"),
    64: ([], ["bench/bench.py"], [], "implemented", None),
    65: ([], [D + "PERFORMANCE.md"], [], "documented", None),
    66: ([], [D + "PERFORMANCE.md"], [], "documented", None),
    67: (["RQ-013"], ["codec.py", "resilience.py", "security.py"], ["test_security_pipeline.ReplayTest.test_bounded_cache_fails_closed"], "implemented", None),
    68: ([], [D + "PERFORMANCE.md"], [], "external", "W-010"),
    69: ([], [D + "PERFORMANCE.md", "deploy/alerts.yml"], [], "documented", None),
    70: ([], ["tools/perf_gate.py"], [], "implemented", None),
    71: (["RQ-043"], ["observability.py"], ["test_subsystems.ObservabilityTest.test_health"], "implemented", None),
    72: (["RQ-044"], ["observability.py"], ["test_subsystems.ObservabilityTest.test_metrics_render_and_cardinality_cap"], "implemented", None),
    73: (["RQ-045"], ["observability.py"], ["test_subsystems.ObservabilityTest.test_logger_schema_and_redaction"], "implemented", None),
    74: (["RQ-046"], ["observability.py"], ["test_subsystems.ObservabilityTest.test_trace_propagated_through_service"], "implemented", None),
    75: (["RQ-044", "RQ-045"], ["observability.py", D + "TELEMETRY_POLICY.md"], ["test_subsystems.ObservabilityTest.test_metrics_render_and_cardinality_cap"], "implemented", None),
    76: (["RQ-026"], ["security.py", "server.py"], ["test_security_pipeline.AuditTest"], "implemented", None),
    77: ([], ["tools/explain.py"], ["test_traceability.ExplainTest"], "implemented", None),
    78: (["RQ-046"], ["observability.py"], [], "partial", "W-012"),
    79: (["RQ-047"], [D + "TELEMETRY_POLICY.md", "observability.py"], ["test_subsystems.ObservabilityTest.test_telemetry_policy"], "implemented", None),
    80: ([], ["deploy/alerts.yml", "deploy/dashboard.json"], [], "partial", "W-012"),
    81: ([], ["tests/test_rpc.py", "tests/test_subsystems.py"], ["test_rpc", "test_subsystems"], "implemented", None),
    82: ([], ["tests/fixtures/golden.json"], ["test_traceability.GoldenFixtureTest"], "implemented", None),
    83: ([], ["tests/test_concurrency_integration.py"], ["test_concurrency_integration.AdjacentLayerTest"], "partial", "W-006"),
    84: ([], ["evidence/runtime_matrix.json", "tools/runtime_matrix.py"], [], "partial", "W-010"),
    85: ([], ["tests/test_wit_codec.py", "tests/corpus"], ["test_wit_codec.PropertyAndFuzzTest"], "implemented", None),
    86: ([], ["tests/test_concurrency_integration.py"], ["test_concurrency_integration.ConcurrencyTest"], "implemented", None),
    87: ([], [D + "THREAT_MODEL.md"], ["test_security_pipeline.AdversarialSuite"], "implemented", None),
    88: ([], ["bench/bench.py", "evidence/bench_results.json"], [], "partial", "W-010"),
    89: ([], ["tests/test_transport.py"], ["test_transport.FaultInjectionTest"], "partial", "W-010"),
    90: ([], ["tools/exit_gate.py", "evidence/EXIT_GATE.json"], [], "implemented", None),
    91: ([], [D + "OPERATIONS.md"], [], "documented", None),
    92: (["RQ-037"], [D + "OPERATIONS.md", "bootstrap.sh"], ["test_security_pipeline.AdversarialSuite.test_ac08_emergency_disable"], "implemented", None),
    93: ([], ["COMPAT_MATRIX.json"], ["test_subsystems.NegotiationTest.test_matrix_consistent_with_code"], "implemented", None),
    94: ([], [D + "OPERATIONS.md"], [], "documented", None),
    95: ([], [D + "OPERATIONS.md", D + "STATE_INVENTORY.md"], ["test_subsystems.OwnershipStateTest.test_restart_preserves_idempotency_disable_and_epoch"], "implemented", None),
    96: ([], [D + "OPERATIONS.md"], [], "documented", None),
    97: ([], [D + "OPERATIONS.md"], [], "documented", None),
    98: ([], [D + "OPERATIONS.md"], [], "partial", "W-001"),
    99: ([], ["WAIVERS.md"], [], "partial", "W-001"),
    100: ([], ["tools/exit_gate.py", D + "OPERATIONS.md"], [], "partial", "W-001"),
}


def build() -> dict:
    checklist_raw = (PKG / "CHECKLIST.json").read_bytes()
    items = json.loads(checklist_raw)["items"]
    rows = []
    for it in items:
        req, arts, tests, status, waiver = MAP[it["ordinal"]]
        rows.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                     "requirements": req, "artifacts": arts, "tests": tests, "status": status, "waiver": waiver})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"schema": "inv61-trace/1", "checklist_sha256": hashlib.sha256(checklist_raw).hexdigest(),
            "summary": dict(sorted(counts.items())), "rows": rows}


def problems(doc: dict) -> list[str]:
    errs = []
    test_src = {p.stem: p.read_text() for p in (PKG / "tests").glob("test_*.py")}
    req_text = (PKG / "docs" / "REQUIREMENTS.md").read_text()
    waivers = (PKG / "WAIVERS.md").read_text()
    for r in doc["rows"]:
        for a in r["artifacts"]:
            if a.startswith("evidence/") or a == "TRACEABILITY.json":
                continue  # produced artifacts; checked by exit gate
            if not (PKG / a).exists():
                errs.append(f"{r['check_id']}: missing artifact {a}")
        for rq in r["requirements"]:
            if f"| {rq} |" not in req_text:
                errs.append(f"{r['check_id']}: unknown requirement {rq}")
        for t in r["tests"]:
            parts = t.split(".")
            src = test_src.get(parts[0])
            if src is None or any(not re.search(rf"\b(class|def) {re.escape(p)}\b", src) for p in parts[1:]):
                errs.append(f"{r['check_id']}: missing test {t}")
        if r["status"] in ("partial", "external") and not (r["waiver"] and f"| {r['waiver']} |" in waivers):
            errs.append(f"{r['check_id']}: {r['status']} without registered waiver")
        if r["status"] == "implemented" and not r["tests"] and not any(a.startswith(("bench/", "tools/")) for a in r["artifacts"]):
            errs.append(f"{r['check_id']}: implemented without test or tool evidence")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    doc = build()
    errs = problems(doc)
    text = json.dumps(doc, indent=2) + "\n"
    if a.check:
        if not OUT.exists() or OUT.read_text() != text:
            errs.append("TRACEABILITY.json is stale; run tools/build_traceability.py")
    else:
        OUT.write_text(text)
    for e in errs:
        print("ERROR", e, file=sys.stderr)
    print(json.dumps(doc["summary"]))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
