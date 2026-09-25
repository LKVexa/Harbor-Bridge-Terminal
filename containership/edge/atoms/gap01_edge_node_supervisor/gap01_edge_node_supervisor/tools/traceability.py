"""Requirements traceability matrix (53): maps each of the 100 CHECKLIST.json
requirements to implementation, evidence and status.  Writes TRACEABILITY.json
and TRACEABILITY.md.  Status: met | partial | exception (EXC-nnn)."""
from __future__ import annotations

import json
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]
T = "tests/"
C = "tests/test_controller.py"
P = "tests/test_production.py"
I = "tests/test_integration.py"  # noqa: E741

# ordinal: (status, implementation, evidence, exception)
M: dict[int, tuple[str, str, str, str]] = {
    1: ("met", "README.md; docs/ARCHITECTURE_DECISIONS.md#ADR-0001", "docs review", ""),
    2: ("met", "README.md Owns/Does-not-own; ADR-0001 table", "docs review", ""),
    3: ("met", "ADR-0001 (scheduler, execution plane, GAP-02, control plane, reporters)", "docs review", ""),
    4: ("met", "store.py (persisted intent) + runtime.observed() reconciled in controller.start", f"{C}::ReconciliationTest", ""),
    5: ("met", "ADR-0005/0006; PLATFORMS_AND_COMPATIBILITY.md", "docs review", ""),
    6: ("partial", "trust classes; per-caller buckets; CAPACITY.md#Fairness", f"{C}::DrainTest", "tenant boundaries delegated to scheduler (ADR-0001)"),
    7: ("met", "REQUIREMENTS.md (SHALL vs MAY); optional pk_core, optional signals", "docs review", ""),
    8: ("met", "README Non-goals; PLATFORMS unsupported rows", "docs review", ""),
    9: ("exception", "OWNERS.md", "-", "EXC-001"),
    10: ("partial", "docs/ARCHITECTURE_DECISIONS.md", "docs review", "EXC-001 (approval)"),
    11: ("partial", "bootstrap.py, inventory.py, runtime.py", f"{T}test_bootstrap_inventory.py", "EXC-004 (wasm/microVM/unikernel)"),
    12: ("met", "REQUIREMENTS.md#Environments; CAPACITY.md profiles", "docs review", ""),
    13: ("met", "REQUIREMENTS.md; CAPACITY.md thresholds; tools/perf_gate.py", "evidence/bench.json", ""),
    14: ("met", "REQUIREMENTS.md#Failure-semantics; errors.ERROR_CATALOG", f"{P}::ErrorModelTest", ""),
    15: ("met", "supervisor.TRANSITIONS; controller._transition", f"{C}::PropertyTest", ""),
    16: ("met", "schemas/*.schema.json; store.migrate; PLATFORMS_AND_COMPATIBILITY.md", "examples/fixtures/compat_*", ""),
    17: ("met", "config.SCHEMA; CAPACITY.md", f"{C}::test_capacity, test_rate_limit", ""),
    18: ("met", "controller partition machine; PARTITION_ALLOWED", f"{C}::test_partition_state_machine", ""),
    19: ("met", "REQUIREMENTS.md#Precedence", f"{C}::test_persistence_failure_enters_emergency", ""),
    20: ("met", "TRACEABILITY.json (this file)", "tools/traceability.py", ""),
    21: ("met", "control socket, probes, state files, runtime adapter, sd_notify: README Interfaces + ADR-0003", "docs review", ""),
    22: ("met", "schemas/*.schema.json; schema_validator.py", f"{T}test_bootstrap_inventory.py::SchemaFixtureTest", ""),
    23: ("met", "security.Authenticator; socket 0600", f"{C}::test_authn_replay_skew; {I}::test_socket_permissions", ""),
    24: ("met", "security.AuthorizationPolicy; OP_CAPABILITY", f"{C}::test_authz_denied_is_audited", ""),
    25: ("met", "request_id idempotency; RateLimiter; drain deadlines; REQUIREMENTS.md", f"{C}::test_idempotent_request_id", ""),
    26: ("met", "errors.py; gap01_error_1.schema.json", f"{P}::ErrorModelTest", ""),
    27: ("met", "PLATFORMS_AND_COMPATIBILITY.md#Version-compatibility", "examples/fixtures/compat_*", ""),
    28: ("met", "CAPACITY.md ceilings; systemd limits", f"{C}::test_oversized, test_capacity", ""),
    29: ("met", "examples/sequences/*.json; examples/fixtures/*.json", "SchemaFixtureTest", ""),
    30: ("partial", "server.py + ProcessAdapter", f"{I}", "EXC-014 (live control plane)"),
    31: ("met", "pyproject.toml; requirements*.txt; sbom.cdx.json", "RELEASE_MANIFEST.json", ""),
    32: ("met", "package (immutable) vs /etc/gap01 (config) vs /var/lib/gap01 (state)", "deploy/systemd", ""),
    33: ("met", "config.SupervisorConfig defaults", f"{P}::ConfigTest", ""),
    34: ("met", "config.validate_knob; load_config signature", f"{P}::ConfigTest", ""),
    35: ("met", "config file + signals file per site; profiles", "CAPACITY.md", ""),
    36: ("partial", "config.provenance (source, sha256, signed); audit of reload_config", f"{P}::test_signed_config", "author identity = signer key only"),
    37: ("met", "frozen config; hot_reload whole-or-nothing; atomic_write", f"{C}::test_config_hot_reload", ""),
    38: ("partial", "RUNBOOKS Day-1 rollback, RB-12; migration forward-only", "docs review", "EXC-015"),
    39: ("met", "config.SecretBoundary; observability.redact", f"{P}::test_secret_boundary, test_redaction", ""),
    40: ("met", "bootstrap.run_phases; RUNBOOKS Day 0", f"{T}test_bootstrap_inventory.py::BootstrapTest", ""),
    41: ("met", "docs/THREAT_MODEL.md", "threat table test column", ""),
    42: ("partial", "roles/capabilities; systemd sandbox", f"{C}::test_authz_denied_is_audited", "EXC-005"),
    43: ("partial", "systemd ProtectSystem/PrivateDevices/IPAddressDeny", "deploy/systemd", "EXC-005"),
    44: ("partial", "caller HMAC auth; config/artifact signatures; software node attestation", f"{P}::SecurityTest", "EXC-002"),
    45: ("met", "security.verify_artifacts; RELEASE_MANIFEST.json", f"{P}::test_artifact_verification", ""),
    46: ("partial", "reclaim proof; process groups", f"{C}::test_unproven_reclaim_never_stops_node", "enforcement delegated to execution plane (ADR-0001); EXC-004"),
    47: ("exception", "UNIX socket local-only; state has no secrets", "-", "EXC-003, EXC-007"),
    48: ("met", "fail-closed: no keys -> boot recovery mode; stale time rejected; partition -> emergency", f"{T}test_bootstrap_inventory.py::test_bad_caller_key_permissions_enter_recovery_mode", ""),
    49: ("met", "store.AuditLog hash chain", f"{P}::test_audit_chain_detects_tamper", ""),
    50: ("partial", "replay, spoofing, injection, escalation tests", f"{C}; {P}", "EXC-012 (independent review)"),
    51: ("met", "THREAT_MODEL + ADR-0005 degraded modes", "docs review", ""),
    52: ("met", "Watchdog; liveness; health staleness", f"{C}::test_readiness_liveness_watchdog", ""),
    53: ("met", "bootstrap retry with exponential backoff; callers retry with request_id", f"{T}test_bootstrap_inventory.py", ""),
    54: ("met", "RateLimiter; pressure blocks admission", f"{C}::test_pressure_blocks_admission", ""),
    55: ("met", "no failover by design: single local authority; restart -> cordoned", f"{C}::ReconciliationTest", ""),
    56: ("met", "partitioned mode; optional health signals quorum", f"{P}::HealthTest", ""),
    57: ("met", "WAL + checkpoint + replay", f"{C}::test_wal_replay_after_crash_before_checkpoint; {I}::ProcessChaosTest", ""),
    58: ("met", "RLock serialization; generations; duplicate-admission refusal; orphan termination", f"{C}::ConcurrencyTest", ""),
    59: ("met", "emergency mode; DISABLED flag; cordon", f"{C}::test_emergency_mode, test_emergency_disable_persists", ""),
    60: ("met", "chaos tests: SIGKILL, torn writes, ENOSPC, corrupt state, clock regression", f"{I}::ProcessChaosTest; {P}::StoreTest", ""),
    61: ("met", "tools/bench.py", "evidence/bench.json", ""),
    62: ("met", "CAPACITY.md; tools/perf_gate.py", "evidence/bench.json", ""),
    63: ("partial", "bench + soak (steady, burst churn, restart)", "evidence/soak.json", "EXC-014 (scale-out on real fleet)"),
    64: ("partial", "per-workload drain/admit cost", "evidence/bench.json", "per-tenant overhead not measured"),
    65: ("met", "non-blocking drain signalling (fixed in v5); single lock", "CHANGELOG 5.0.0", ""),
    66: ("met", "local UNIX IPC; in-memory aggregation; not applicable beyond", "ADR-0003", ""),
    67: ("met", "bounded rings, windows, queue, sizes", "CAPACITY.md; evidence/soak.json", ""),
    68: ("exception", "-", "-", "EXC-008"),
    69: ("met", "CAPACITY.md saturation signals", "docs review", ""),
    70: ("met", "tools/perf_gate.py in CI release job", ".github/workflows/ci.yml", ""),
    71: ("met", "/livez /readyz /metrics; status; diagnostics (config, version)", f"{I}::test_full_lifecycle_with_real_processes", ""),
    72: ("met", "observability.Metrics", f"{P}::test_metrics_low_cardinality", ""),
    73: ("met", "JSON logs with event_id, request_id, trace_id", "docs/OBSERVABILITY.md", ""),
    74: ("partial", "Tracer traceparent; trace_id in audit", f"{P}::test_trace_propagation", "EXC-013 (exporter)"),
    75: ("met", "diagnostics redacted", f"{P}::test_redaction", ""),
    76: ("met", "last_reason; audit per decision; drain escalation text", f"{C}::test_audit_chain_intact_after_run", ""),
    77: ("met", "diagnostics explain bundle", "docs/OBSERVABILITY.md", ""),
    78: ("partial", "version + boot attestation in diagnostics", "boot_attestation.json", "release-lineage/infra-graph link needs control plane"),
    79: ("met", "OBSERVABILITY.md retention/privacy", "docs review", ""),
    80: ("partial", "deploy/prometheus/gap01-alerts.yml", "docs review", "EXC-013 (dashboards)"),
    81: ("met", "unit tests", f"{T}test_supervisor.py; {P}", ""),
    82: ("met", "schema fixtures + status/drain/health validation", "SchemaFixtureTest; test_status_matches_schema", ""),
    83: ("partial", "process-runtime integration", f"{I}", "EXC-004, EXC-014"),
    84: ("exception", "CI matrix defined", ".github/workflows/ci.yml", "EXC-009"),
    85: ("met", "FuzzTest (500 random inputs)", f"{C}::FuzzTest", ""),
    86: ("met", "ConcurrencyTest", f"{C}::ConcurrencyTest", ""),
    87: ("met", "THREAT_MODEL test column", "tests", ""),
    88: ("met", "bench, soak, burst churn", "evidence/*.json", ""),
    89: ("met", "partition, reconnect, restart tests", f"{C}::SafetyModesTest", ""),
    90: ("met", "tools/evidence.py -> evidence/evidence.json", "evidence/evidence.json", ""),
    91: ("partial", "SLOTracker; SUPPORT.md", f"{C}::PropertyTest (SLO violations = 0)", "support commitments need owner (EXC-001)"),
    92: ("partial", "RUNBOOKS Day-1, RB-13", f"{C}::test_emergency_disable_persists", "EXC-015"),
    93: ("met", "PLATFORMS_AND_COMPATIBILITY.md", "docs review", ""),
    94: ("met", "SECURITY.md; SUPPORT.md", "docs review", ""),
    95: ("met", "StateStore.backup/restore; migrate", f"{P}::test_backup_restore, test_migration", ""),
    96: ("met", "RUNBOOKS Day 0/1/2", "docs review", ""),
    97: ("met", "RUNBOOKS incident severity", "docs review", ""),
    98: ("exception", "-", "-", "EXC-001 (recurring reviews need owners)"),
    99: ("met", "EXCEPTIONS.md", "docs review", ""),
    100: ("partial", "tools/exit_gate.py", "evidence/exit_gate.json", "gate returns NO_GO/CONDITIONAL until blockers close"),
}


def main() -> None:
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    rows = []
    for it in items:
        st, impl, ev, exc = M[it["ordinal"]]
        rows.append({"check_id": it["check_id"], "ordinal": it["ordinal"], "dimension": it["dimension"],
                     "requirement": it["requirement"], "status": st, "implementation": impl,
                     "evidence": ev, "exception": exc, "owner": "unassigned (EXC-001)"})
    counts = {s: sum(r["status"] == s for r in rows) for s in ("met", "partial", "exception")}
    (PKG / "TRACEABILITY.json").write_text(json.dumps({"element": "GAP-01", "version": "5.0.0",
                                                       "summary": counts, "rows": rows}, indent=2) + "\n")
    md = ["# GAP-01 Requirements Traceability Matrix (v5.0.0)", "",
          f"**Summary:** {counts['met']} met · {counts['partial']} partial · {counts['exception']} exception "
          "(of 100). Owner for every row: unassigned (EXC-001).", "",
          "| ID | Dimension | Status | Implementation | Evidence | Exception / gap |", "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['check_id']} | {r['dimension']} | {r['status']} | {r['implementation']} | "
                  f"{r['evidence']} | {r['exception']} |")
    (PKG / "TRACEABILITY.md").write_text("\n".join(md) + "\n")
    print(counts)


if __name__ == "__main__":
    main()
