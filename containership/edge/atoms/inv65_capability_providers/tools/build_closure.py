"""Build MISSING_COMPONENTS_4.3.0.json: disposition of M01-M40 against the
remediation checklist, with every cited path verified to exist."""
from __future__ import annotations

import json
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]
t = "tests/"
C = [
 ("M01", "P1", "blocked", ["docs/master/SOURCE_PROVENANCE.md"], [t+"test_release_tooling.py"], "authoritative MASTER.md corpus not supplied; not fabricated"),
 ("M02", "P0", "blocked", ["docs/dependencies/pk_core.md", "lock/pk_core.lock.json", "ci/scripts/check_pk_core.py", "pyproject.toml"], [], "pk_core source/version/digest not supplied; runtime decoupled from it; gate fails check_pk_core"),
 ("M03", "P0", "closed-local", ["schemas/", "schemas/COMPATIBILITY.md", "schemas/SCHEMA_LOCK.json"], [t+"contract/test_golden_vectors.py"], None),
 ("M04", "P0", "partial", ["host/server.py", "host/bootstrap.py", "transport/http_adapter.py", "deployment/provider-host.service.json"], [t+"integration/test_host_http.py"], "HTTP/JSON transport only; WIT/RPC mapping belongs to INV-61; mTLS path not exercised with real certificates"),
 ("M05", "P0", "closed-local", ["state/store.py", "state/migrations.py"], [t+"fault/test_state_recovery.py"], None),
 ("M06", "P0", "closed-local", ["identity/context.py", "schemas/identity_context/v1.json", "docs/identity-trust-boundaries.md"], [t+"security/test_identity_binding.py"], None),
 ("M07", "P0", "partial", ["authn/authenticator.py", "docs/authentication.md"], [t+"security/test_authentication.py"], "HMAC workload-token adapter; production SPIFFE/attested issuer from INV-60 must be plugged in"),
 ("M08", "P0", "closed-local", ["authz/decision.py", "schemas/authz_decision/v1.json", "docs/authorization-integration.md"], [t+"security/test_authorization_enforcement.py"], None),
 ("M09", "P0", "partial", ["secret_refs/resolver.py", "schemas/secret_ref/v1.json", "docs/secret-lifecycle.md"], [t+"security/test_secret_handling.py", t+"integration/test_adjacent_layers.py"], "INV-55 exercised through an in-memory fixture backend; real INV-55 client absent"),
 ("M10", "P1", "closed-local", ["config/model.py"], [t+"test_runtime_units.py"], None),
 ("M11", "P1", "closed-local", ["lifecycle/state_machines.py", "docs/lifecycle-state-machines.md"], [t+"test_runtime_units.py"], None),
 ("M12", "P1", "closed-local", ["registry/model.py", "schemas/provider_registration/v1.json"], [t+"integration/test_registry_negotiation.py"], None),
 ("M13", "P1", "closed-local", ["errors/mapping.py", "schemas/pk_provider_error/v1.json", "docs/error-catalog.md"], [t+"contract/test_error_compatibility.py"], None),
 ("M14", "P0", "closed-local", ["runtime/call_control.py", "runtime/idempotency.py", "schemas/call_metadata/v1.json"], [t+"test_runtime_units.py", t+"fault/test_fault_scenarios.py"], None),
 ("M15", "P0", "closed-local", ["runtime/admission.py", "runtime/quotas.py", "runtime/circuit_breaker.py"], [t+"test_runtime_units.py", "benchmarks/harness.py"], None),
 ("M16", "P1", "closed-local", ["health/model.py", "health/probes.py", "schemas/pk_provider_health/v1.json"], [t+"test_runtime_units.py", t+"integration/test_host_http.py"], None),
 ("M17", "P0", "partial", ["resilience/failover.py", "resilience/fencing.py", "docs/failure-mode-matrix.md"], [t+"fault/test_failover_splitbrain.py"], "lease manager is in-process; a shared lease service (etcd-like) across hosts is external"),
 ("M18", "P0", "closed-local", ["audit/emitter.py", "audit/verification.py", "schemas/audit_event/v1.json"], [t+"security/test_audit_chain.py"], None),
 ("M19", "P0", "partial", ["crypto/at_rest.py", "crypto/transport.py", "docs/key-management.md"], [t+"security/test_key_rotation.py"], "KMS/HSM integration and certificate issuance external; mTLS not exercised end-to-end"),
 ("M20", "P1", "partial", ["supply_chain/trust.py", "supply_chain/provider_catalog.json", "sbom/", "provenance/"], [t+"integration/test_registry_negotiation.py"], "SBOM/provenance generated but UNSIGNED (owner-held key)"),
 ("M21", "P1", "partial", ["observability/telemetry.py", "docs/telemetry-policy.md"], [t+"test_runtime_units.py"], "no exporter to a real metrics/trace backend; no release-lineage correlation"),
 ("M22", "P2", "partial", ["dashboards/provider-overview.json", "alerts/provider-rules.json", "docs/oncall/provider-alerts.md"], [t+"monitoring/test_alert_rules.py"], "definitions validated against emitted metrics; not loaded into a monitoring stack"),
 ("M23", "P0", "blocked", [t+"integration/test_adjacent_layers.py"], [t+"integration/test_adjacent_layers.py"], "INV-60/55/64/61 repositories absent; seams tested against contract stubs only"),
 ("M24", "P1", "closed-local", ["conformance/fixtures/v1/", "conformance/fixtures/invalid/", "conformance/mixed_version_matrix.json"], [t+"contract/test_golden_vectors.py"], None),
 ("M25", "P0", "closed-local", ["fuzz/harness.py", "docs/threat-model.md"], [t+"security/test_adversarial.py"], None),
 ("M26", "P0", "partial", ["tests/fault/fault_matrix.json", "evidence/fault-results.json"], [t+"fault/"], "network partition simulated via lease clock; no real disaster/partition environment"),
 ("M27", "P1", "partial", ["benchmarks/harness.py", "benchmarks/baselines/local.json", "benchmarks/scenarios.json", "evidence/performance-results.json"], [t+"test_release_tooling.py"], "single host; fleet-scale not run"),
 ("M28", "P1", "partial", ["compatibility/matrix.json", "compatibility/policy.md", ".github/workflows/inv65.yml", "evidence/compatibility-results.json"], [], "only CPython 3.11 x86_64 linux executed; CI matrix defined but not run"),
 ("M29", "P1", "partial", [".github/workflows/inv65.yml", "ci/scripts/ci.sh", "release/manifest.schema.json", "docs/release-process.md", "tools/release_gate.py"], [], "CI defined, executed locally only; release signing not performed"),
 ("M30", "P0", "partial", ["evidence/pk_evidence.jsonl", "conformance/PK_GATE_RESULTS.json", "schemas/evidence_record/v1.json", "tools/verify_evidence.py"], [t+"test_release_tooling.py"], "evidence produced and verified; pk_core 100-item conformance still not_run"),
 ("M31", "P1", "closed-local", ["traceability/INV65_RTM.json", "tools/build_rtm.py", "tools/check_rtm.py", "docs/traceability.md"], [t+"test_release_tooling.py"], None),
 ("M32", "P1", "partial", ["docs/adr/ADR-0001-provider-runtime.md", "docs/threat-model.md", "docs/runbooks/", "docs/ownership-escalation.md"], [], "owner/reviewer UNASSIGNED; ADR PROPOSED, not approved"),
 ("M33", "P1", "partial", ["rollout/controller.py", "rollout/canary-policy.json", "docs/runbooks/rollout-rollback.md"], [t+"integration/test_rollout.py"], "not exercised against production-like durable state"),
 ("M34", "P2", "partial", ["governance/VULNERABILITY_POLICY.md", "governance/EOL_POLICY.md", "governance/waivers.json", "governance/review-calendar.md"], [t+"test_release_tooling.py"], "waiver owners UNASSIGNED; reviews never held"),
 ("M35", "P1", "closed-local", ["tools/backup_state.py", "state/migrations.py", "docs/runbooks/backup-restore.md"], [t+"fault/test_state_recovery.py"], None),
 ("M36", "P1", "partial", ["pyproject.toml", "lock/constraints.txt"], [t+"test_release_tooling.py"], "wheel builds reproducibly (verified in a venv); lock has no hashes (no approved mirror); pk_core unpinned"),
 ("M37", "P2", "blocked", ["NOTICE", "THIRD-PARTY-NOTICES.md", "docs/licensing.md"], [], "licence choice is the owner's; not invented"),
 ("M38", "P1", "closed-local", ["fixtures/providers/keyvalue.py", "fixtures/providers/http.py", "fixtures/providers/broker.py"], [t+"conformance/test_adapter_suite.py"], None),
 ("M39", "P1", "partial", ["slo/SLO.json", "slo/measurement.md", "slo/error_budget.py", "evidence/slo-results.json"], [t+"test_runtime_units.py"], "measured on one host; isolation/restart SLIs are test-suite proxies"),
 ("M40", "P1", "closed-local", ["residency/engine.py", "schemas/residency_policy/v1.json"], [t+"test_runtime_units.py", t+"fault/test_failover_splitbrain.py"], None),
]
DEVIATIONS = [
 "secrets/ -> secret_refs/: a package directory named 'secrets' shadows the stdlib 'secrets' module whenever the package dir is on sys.path",
 "*.yaml deliverables -> *.json: the runtime is stdlib-only and Python has no stdlib YAML parser",
 "lifecycle/provider_state.py + link_state.py -> lifecycle/state_machines.py (one module, both machines)",
 "observability/{metrics,logging,tracing,explain}.py -> observability/telemetry.py (one module)",
 "registry/client.py -> registry/model.py ProviderRegistry.discover (in-process); remote client = HTTP /v1/contract",
 "tests/security/test_residency_constraints.py, tests/test_config_transactions.py, tests/test_lifecycle_transitions.py, tests/test_call_control.py, tests/test_health_state.py -> classes in tests/test_runtime_units.py",
 "authn/ trust-root configuration -> host.json keys (docs/authentication.md)",
]


def build():
    rows, missing = [], []
    for mid, pri, status, deliv, tests, blocker in C:
        for p in deliv + tests:
            if not (PKG / p).exists():
                missing.append(f"{mid}: {p}")
        rows.append({"id": mid, "priority": pri, "status": status, "deliverables": deliv, "tests": tests, "remaining": blocker})
    if missing:
        raise SystemExit("missing paths: " + "; ".join(missing))
    from collections import Counter
    return {"element": "INV-65", "version": "4.3.0", "audit_date": "2026-09-22", "input": "4.2.0 hardened + remediation checklist 4.2.0",
            "summary": dict(Counter(r["status"] for r in rows)),
            "p0_open": [r["id"] for r in rows if r["priority"] == "P0" and r["status"] != "closed-local"],
            "status_vocabulary": {"closed-local": "implemented with passing executable tests in this archive; nothing external required",
                                  "partial": "implemented and tested locally; a named external condition remains",
                                  "blocked": "cannot be completed inside this archive without inventing inputs"},
            "components": rows, "deviations_from_checklist_paths": DEVIATIONS}


if __name__ == "__main__":
    (PKG / "MISSING_COMPONENTS_4.3.0.json").write_text(json.dumps(build(), indent=1) + "\n")
    print(json.dumps(build()["summary"]), build()["p0_open"])
