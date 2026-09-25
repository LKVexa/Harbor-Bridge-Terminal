"""Canonical source of truth for the INV-38 v4.2.0 missing-component remediation.

Every status here is assigned against the checklist's own rule (README/Completion
rules): a requirement is only DONE when repository-owned implementation/spec AND
reproducible evidence exist that are sufficient for the stated production scope.
Reference-model behaviour is NOT a substitute for hardware/pk_core-backed
evidence, so any RDMA/NIC/IOMMU/provider or pk_core-dependent certification is
recorded as IN_PROGRESS (artifact present, model-level tests only) or BLOCKED
(cannot advance without external hardware/pk_core), never DONE.

status  : DONE | IN_PROGRESS | BLOCKED | WAIVED | PRESENT | OPEN
  DONE        - repo artifact + in-repo reproducible evidence, sufficient at the
                achievable (model/spec) scope for this requirement.
  IN_PROGRESS - repo artifact exists and model-level tests pass, but production
                evidence still requires hardware / pk_core / live infrastructure.
  BLOCKED     - a plan/spec artifact exists but the requirement cannot be
                certified at all from this ZIP; the blocker is named.
  PRESENT     - was not in the 50 MISSING items (already satisfied per prior audit);
                out of scope for this remediation pass.
"""
from __future__ import annotations

# id: (dimension, priority, status, blocker_or_note, [artifacts], [tests], [evidence])
ITEMS: dict[str, tuple] = {
 "C009": ("Architecture & Scope","P1","IN_PROGRESS","Escalation-drill (C009-T07) evidence needs a live paging integration.",
          ["docs/OWNERSHIP.md",".github/CODEOWNERS","ops/escalation.yaml"],["tests/test_governance.py"],["ci/repo-integrity check"]),
 "C010": ("Architecture & Scope","P1","IN_PROGRESS","Backend benchmark evidence (C010-T07) needs RDMA hardware.",
          ["docs/adr/ADR-0038-kernel-bypass-backend.md","architecture/rdma-decision-record.yaml"],["tests/test_artifacts_present.py"],["ADR reviewed+versioned"]),
 "C012": ("Requirements & Semantics","P1","IN_PROGRESS","Per-context conformance across real NIC/SR-IOV needs hardware.",
          ["specs/deployment-contexts.md","specs/deployment-contexts.yaml"],["tests/test_deployment_contexts.py"],["profile schema validated"]),
 "C014": ("Requirements & Semantics","P1","DONE","Outcome model fully realized and tested at model scope.",
          ["specs/outcome-semantics.md","schemas/outcome-v1.schema.json","outcomes.py"],["tests/test_outcomes.py"],["table-driven reason-code stability"]),
 "C015": ("Requirements & Semantics","P1","DONE","Lifecycle state machine + illegal-transition tests pass.",
          ["specs/lifecycle-state-machine.md","schemas/lifecycle-v1.schema.json","lifecycle.py"],["tests/test_lifecycle.py"],["model-based legal/illegal transitions"]),
 "C019": ("Requirements & Semantics","P1","DONE","Precedence lattice + decision-table tests pass.",
          ["policy/constraint-precedence.md","policy/constraint-precedence.yaml","precedence.py"],["tests/test_precedence.py"],["pairwise conflict determinism"]),
 "C020": ("Requirements & Semantics","P1","DONE","RTM generated from canonical data + CI validator.",
          ["traceability/INV38_RTM.csv","traceability/INV38_RTM.json","rtm_tools.py"],["tests/test_rtm.py"],["100 unique IDs, no PASS w/o evidence"]),
 "C022": ("Interfaces & Integration","P0","IN_PROGRESS","Multi-language binding generation (C022-T07) needs a real IDL toolchain.",
          ["schemas/pk_bypass_mr_v1.schema.json","schemas/pk_bypass_post_v1.schema.json","schemas/pk_bypass_cq_v1.schema.json","schemas/pk_bypass_error_v1.schema.json","schemas/golden/"],["tests/test_schemas_golden.py"],["golden valid/boundary/malformed vectors"]),
 "C023": ("Interfaces & Integration","P0","IN_PROGRESS","Real credential/trust-root integration needs identity service.",
          ["security/authentication.md","security/trust-roots.yaml","authz.py"],["tests/test_authz.py"],["negative authn tests (model)"]),
 "C024": ("Interfaces & Integration","P0","IN_PROGRESS","OS/device-layer least privilege (VF/IOMMU) needs hardware.",
          ["security/authorization.md","security/capabilities.yaml","authz.py"],["tests/test_authz.py"],["cross-tenant/denial tests (model)"]),
 "C027": ("Interfaces & Integration","P1","IN_PROGRESS","Real-backend adapter transcripts needed for full matrix.",
          ["compatibility/protocol-negotiation.md","compatibility/version-policy.yaml","negotiation.py"],["tests/test_negotiation.py"],["N/N-1 downgrade-protection tests"]),
 "C031": ("Implementation & Configuration","P0","BLOCKED","Hardware/firmware/driver qualification requires physical RDMA NICs + IOMMU.",
          ["platform/rdma-stack.lock.yaml","platform/hardware-qualification.yaml","platform/provider-matrix.md","platform/preflight.py"],["tests/test_preflight.py"],["preflight refuses missing stack (model)"]),
 "C032": ("Implementation & Configuration","P1","DONE","Boundary documented + layout schema + drift check tested.",
          ["architecture/artifact-config-state-boundary.md","config/layout.schema.json"],["tests/test_config_layout.py"],["startup drift detection"]),
 "C036": ("Implementation & Configuration","P1","DONE","Provenance schema + redaction + history tested.",
          ["config/provenance.schema.json","config/history/README.md","config_provenance.py"],["tests/test_config_provenance.py"],["provenance bind + redaction tests"]),
 "C037": ("Implementation & Configuration","P1","DONE","Prepare/validate/stage/commit txn engine + fault tests.",
          ["config/transaction-protocol.md","config/transaction.schema.json","config_txn.py"],["tests/test_config_txn.py"],["atomic commit + rollback fault-injection"]),
 "C042": ("Security, Trust & Isolation","P0","IN_PROGRESS","Runtime privilege drop enforcement needs a real OS deployment.",
          ["security/least-privilege.md","security/privilege-matrix.yaml","privilege_check.py"],["tests/test_privilege.py"],["capability inventory static check"]),
 "C043": ("Security, Trust & Isolation","P0","IN_PROGRESS","Sandbox-escape tests need a real sandboxed host.",
          ["security/ambient-authority-inventory.yaml","security/sandbox-profile.json","privilege_check.py"],["tests/test_privilege.py"],["ambient-authority self-check (model)"]),
 "C044": ("Security, Trust & Isolation","P0","IN_PROGRESS","Peer/provider mutual auth needs live identities/attestation.",
          ["security/trust-bootstrap.md","security/peer-auth-policy.yaml","authz.py"],["tests/test_authz.py"],["forged/expired identity tests (model)"]),
 "C045": ("Security, Trust & Isolation","P0","DONE","SBOM + provenance + signed-manifest verify + tamper tests in-repo.",
          ["supply-chain/verification-policy.yaml","sbom/inv38.sbom.json","provenance/build-provenance.json","supply_chain.py"],["tests/test_supply_chain.py"],["tamper-detection blocks activation"]),
 "C048": ("Security, Trust & Isolation","P0","IN_PROGRESS","Live KMS/attestation/time outage behaviour needs those services.",
          ["security/dependency-outage-semantics.md","security/fail-safe-matrix.yaml","failsafe.py"],["tests/test_failsafe.py"],["cache-age bound + fail-closed tests (model)"]),
 "C049": ("Security, Trust & Isolation","P0","DONE","Hash-chained audit log + offline verifier + injection tests.",
          ["audit/event.schema.json","audit/integrity.md","audit_log.py"],["tests/test_audit_log.py"],["delete/insert/reorder/tamper all detected"]),
 "C052": ("Resilience & Failure Handling","P0","IN_PROGRESS","Real device-reset/stall detection latency needs hardware.",
          ["resilience/health-stall-detection.md","resilience/thresholds.yaml","health_stall.py"],["tests/test_health_stall.py"],["synthetic stall detection (model)"]),
 "C053": ("Resilience & Failure Handling","P0","DONE","Bounded retry+backoff+jitter engine, deterministic tests.",
          ["resilience/retry-policy.yaml","resilience/retry-safety-matrix.md","retry.py"],["tests/test_retry.py"],["no retry storm / no dup completion"]),
 "C057": ("Resilience & Failure Handling","P0","IN_PROGRESS","Real crash/device-reset recovery needs hardware.",
          ["resilience/state-recovery.md","schemas/recovery-checkpoint-v1.schema.json","recovery.py"],["tests/test_recovery.py"],["generation/epoch stale rejection (model)"]),
 "C058": ("Resilience & Failure Handling","P0","IN_PROGRESS","True partition/fencing needs a multi-node cluster.",
          ["resilience/ownership-fencing.md","resilience/lease-epoch.schema.json","fencing.py"],["tests/test_fencing.py"],["stale-epoch rejection (model)"]),
 "C061": ("Performance & Resource Efficiency","P1","BLOCKED","Reproducible latency/throughput/power baselines require RDMA hardware.",
          ["benchmarks/baseline-plan.yaml","benchmarks/baseline-results.json","benchmarks/environment.json"],["tests/performance/README.md"],["plan + kernel-path model harness only"]),
 "C063": ("Performance & Resource Efficiency","P1","BLOCKED","Steady/burst/overload campaign requires hardware + load infra.",
          ["benchmarks/scenarios.yaml","benchmarks/load-results/README.md"],["tests/performance/README.md"],["scenario definitions only"]),
 "C064": ("Performance & Resource Efficiency","P1","BLOCKED","Per-tenant overhead measurement requires hardware.",
          ["benchmarks/tenant-overhead.yaml","benchmarks/tenant-overhead-results.json"],[],["plan only"]),
 "C068": ("Performance & Resource Efficiency","P1","BLOCKED","Power/thermal measurement requires calibrated edge hardware.",
          ["benchmarks/power-thermal-plan.yaml","benchmarks/power-thermal-results.json"],[],["plan only"]),
 "C070": ("Performance & Resource Efficiency","P0","IN_PROGRESS","Gate mechanism done+tested; approved baseline BLOCKED on hardware (C061).",
          ["ci/performance-gate.yaml","benchmarks/approved-baseline.json","perf_gate.py"],["tests/test_perf_gate.py"],["regression diff + fail logic tested"]),
 "C071": ("Observability & Explainability","P1","DONE","Health/readiness snapshot, secret-free, generation-consistent.",
          ["observability/health.schema.json","observability/status-contract.md","status.py"],["tests/test_status.py"],["liveness/readiness + dep-stale tests"]),
 "C073": ("Observability & Explainability","P1","DONE","Structured log schema + redaction + injection safety tested.",
          ["observability/logging.schema.json","observability/logging-policy.md","logging_schema.py"],["tests/test_logging.py"],["redaction + control-char escape tests"]),
 "C074": ("Observability & Explainability","P1","IN_PROGRESS","Cross-boundary trace continuity needs adjacent live components.",
          ["observability/tracing.md","observability/trace-propagation-tests/README.md","tracing.py"],["tests/test_tracing.py"],["baggage sanitize + span map (model)"]),
 "C075": ("Observability & Explainability","P1","DONE","Redaction policy + bounded diagnostics + adversarial tests.",
          ["observability/diagnostics.md","observability/redaction-policy.yaml","logging_schema.py"],["tests/test_logging.py"],["cross-tenant/secret-leak tests"]),
 "C076": ("Observability & Explainability","P1","DONE","Decision records: every branch has a reason code (tested).",
          ["observability/decision-record.schema.json","observability/reason-codes.yaml","decisions.py"],["tests/test_decisions.py"],["no fallback/reject without decision record"]),
 "C077": ("Observability & Explainability","P1","DONE","Operator explain view (human+machine) with golden fixtures.",
          ["ops/explain-view.md","tools/inv38-explain"],["tests/test_decisions.py"],["golden incident fixtures"]),
 "C078": ("Observability & Explainability","P1","IN_PROGRESS","Live infra-graph correlation needs the graph service.",
          ["observability/lineage-correlation.md","observability/resource-identity.schema.json"],["tests/test_artifacts_present.py"],["resource-identity schema validated"]),
 "C079": ("Observability & Explainability","P1","DONE","Telemetry retention/sampling/export policy + conformance test.",
          ["observability/telemetry-policy.md","observability/retention.yaml","telemetry_policy.py"],["tests/test_telemetry_policy.py"],["security events never sampled (tested)"]),
 "C080": ("Observability & Explainability","P1","IN_PROGRESS","Dashboards/alerts validated against synthetic incidents; live wiring pending.",
          ["observability/dashboards/inv38-overview.json","observability/alerts/inv38-alerts.yaml"],["tests/test_alerts.py"],["alert-rule schema + zero-budget page rule"]),
 "C084": ("Testing & Certification","P0","BLOCKED","Real CPU/hypervisor/provider/NIC rows require that hardware.",
          ["compatibility/test-matrix.yaml","tests/compatibility/README.md","tests/compatibility/test_reference_row.py"],["tests/compatibility/test_reference_row.py"],["reference row only; hw rows unsupported-until-qualified"]),
 "C085": ("Testing & Certification","P0","DONE","Property/fuzz harness over schema + address arithmetic runs in CI.",
          ["tests/fuzz/README.md","tests/fuzz/fuzz_transport.py","tests/fuzz/corpus/"],["tests/fuzz/fuzz_transport.py"],["structure-aware fuzz + regression corpus"]),
 "C088": ("Testing & Certification","P0","BLOCKED","Soak/fleet at scale requires hardware + multi-node fleet.",
          ["tests/performance/README.md","tests/soak/README.md","tests/fleet/README.md","tests/soak/test_model_soak.py"],["tests/soak/test_model_soak.py"],["model soak (leak/counter) only"]),
 "C089": ("Testing & Certification","P0","IN_PROGRESS","Real partition/device-reset needs hardware; model faults tested.",
          ["tests/disaster/README.md","tests/partition/README.md","tests/reconnect/README.md","tests/disaster/test_model_faults.py"],["tests/disaster/test_model_faults.py"],["model crash/stale-key/fencing faults"]),
 "C090": ("Testing & Certification","P0","IN_PROGRESS","Acceptance builder+gate+tamper tests DONE; full certification CONDITIONAL_GO (pk_core/hw evidence absent).",
          ["release/acceptance.schema.json","release/PK_ACCEPTANCE.json","release/attestations/","release_gate.py"],["tests/test_release_gate.py"],["gate rejects tampered/expired/skip-as-pass"]),
 "C093": ("Operations, Release & Governance","P1","IN_PROGRESS","Rows for real backend stacks pending qualification.",
          ["compatibility/SUPPORTED_VERSIONS.md","compatibility/supported-versions.yaml","version_support.py"],["tests/test_version_support.py"],["preflight rejects unsupported combo (model)"]),
 "C094": ("Operations, Release & Governance","P1","DONE","SECURITY.md + patch/EOL policy authored; tabletop template included.",
          ["SECURITY.md","docs/PATCH_AND_EOL_POLICY.md"],["tests/test_artifacts_present.py"],["policy documents present + linked"]),
 "C095": ("Operations, Release & Governance","P1","IN_PROGRESS","Device-replacement rebuild needs hardware; reconstruction logic tested.",
          ["ops/state-reconstruction.md","ops/migration.md","tests/recovery/test_reconstruction.py"],["tests/recovery/test_reconstruction.py"],["empty-node reconstruction (model)"]),
 "C097": ("Operations, Release & Governance","P1","DONE","Incident response + severity + runbooks authored.",
          ["ops/INCIDENT_RESPONSE.md","ops/severity.yaml","ops/runbooks/"],["tests/test_severity.py"],["severity schema validated"]),
 "C098": ("Operations, Release & Governance","P1","DONE","Review schedule + governance CI check for overdue reviews.",
          ["governance/review-schedule.yaml","governance/review-records/README.md","governance_checks.py"],["tests/test_governance_checks.py"],["overdue-review blocks release (tested)"]),
 "C099": ("Operations, Release & Governance","P1","DONE","Waiver/tech-debt register + validator (dup/expiry/dangling).",
          ["governance/waivers.schema.json","governance/WAIVERS.json","governance/TECH_DEBT.md","governance_checks.py"],["tests/test_governance_checks.py"],["expired/unapproved waiver blocks release"]),
}

# All 100 IDs C001..C100; ones not in ITEMS were PRESENT before this pass.
ALL_IDS = [f"C{n:03d}" for n in range(1, 101)]

def full_status() -> dict[str, dict]:
    out = {}
    for cid in ALL_IDS:
        if cid in ITEMS:
            dim, pri, st, note, arts, tests, ev = ITEMS[cid]
            out[cid] = {"id": f"INV-38-{cid}", "dimension": dim, "priority": pri,
                        "status": st, "note": note, "artifacts": arts,
                        "tests": tests, "evidence": ev, "in_remediation_scope": True}
        else:
            out[cid] = {"id": f"INV-38-{cid}", "dimension": "-", "priority": "-",
                        "status": "PRESENT", "note": "Not in the 50 MISSING items; satisfied per prior audit.",
                        "artifacts": [], "tests": [], "evidence": [], "in_remediation_scope": False}
    return out
