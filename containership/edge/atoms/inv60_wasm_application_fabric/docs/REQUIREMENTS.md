# Normative requirements (M08) — generated from requirements.json

Terminology: RFC 2119 / RFC 8174. Version 1.0.0. Deployment classes: central, edge, partially-connected, disconnected.

| id | level | kind | requirement | verified by | criticality | owner |
|---|---|---|---|---|---|---|
| REQ-MEM-01 | SHALL | functional | Membership SHALL admit only authenticated, attested hosts that enrol themselves. | `test_security.Adversarial.test_T10_host_cannot_enrol_other_host` | release-blocking | UNASSIGNED |
| REQ-MEM-02 | SHALL | functional | A host silent for lost_after_s SHALL be declared lost and its components rescheduled only by the quorum lease holder. | `test_resilience.Membership.test_failover_without_quorum_refused` | release-blocking | UNASSIGNED |
| REQ-ART-01 | SHALL | functional | The fabric SHALL instantiate only bytes whose sha256 equals the reference. | `test_security.ArtifactSigning.test_registry_swap_after_verification_detected` | release-blocking | UNASSIGNED |
| REQ-ART-02 | SHALL | security | Artifacts SHALL carry a valid signature from a trusted, unrevoked signer with provenance level >= policy minimum. | `test_security.ArtifactSigning.test_low_provenance_level` | release-blocking | UNASSIGNED |
| REQ-LIFE-01 | SHALL | functional | Lifecycle changes SHALL follow the published transition tables; illegal transitions SHALL return ILLEGAL_TRANSITION without mutation. | `test_semantics.Lifecycle.test_model_based_random_sequences` | release-blocking | UNASSIGNED |
| REQ-LIFE-02 | SHALL | functional | Stopping a component SHALL revoke its links. | `test_runtime.LatticeRuntimeTest.test_lifecycle_revokes_links` | release-blocking | UNASSIGNED |
| REQ-LINK-01 | SHALL | security | A call SHALL be refused unless an unexpired, unrevoked grant names the caller, tenant and operation. | `test_security.Authorization.test_operation_not_in_grant` | release-blocking | UNASSIGNED |
| REQ-ROUTE-01 | SHALL | functional | Calls SHALL route only to instances on live hosts. | `test_runtime.LatticeRuntimeTest.test_membership_failover_and_last_host_refusal_are_atomic` | release-blocking | UNASSIGNED |
| REQ-FAIL-01 | SHALL | functional | Failover SHALL never place a component outside its allowed regions; with no eligible host it SHALL mark the component failed. | `test_resilience.Placement.test_failover_with_no_residency_target_fails_component` | release-blocking | UNASSIGNED |
| REQ-AUTH-01 | SHALL | security | Every operation SHALL authenticate the caller and SHALL deny by default. | `test_security.Authorization.test_unknown_action_denied` | release-blocking | UNASSIGNED |
| REQ-AUTH-02 | SHALL | security | Identity or policy dependency failure SHALL fail closed. | `test_security.Authentication.test_dependency_unavailable_fails_closed` | release-blocking | UNASSIGNED |
| REQ-RES-01 | SHALL | non-functional | Every public operation SHALL return a versioned Result envelope with a stable code. | `test_semantics.ResultModel.test_public_boundary_never_raises` | release-blocking | UNASSIGNED |
| REQ-RES-02 | SHALL | non-functional | Non-idempotent operations SHALL NOT be retried automatically without an idempotency key. | `test_resilience.Retries.test_non_idempotent_not_retried` | release-blocking | UNASSIGNED |
| REQ-LIM-01 | SHALL | non-functional | Payload, rate, in-flight, component and link limits SHALL be enforced per tenant before allocation. | `test_semantics.ResourceLimits.test_inflight_per_tenant_and_global` | release-blocking | UNASSIGNED |
| REQ-PART-01 | SHALL | functional | An isolated host SHALL serve existing links for at most isolated_serving_s and SHALL NOT accept new authority. | `test_resilience.Membership.test_fabric_partition_blocks_mutation_serves_existing` | release-blocking | UNASSIGNED |
| REQ-DUR-01 | SHALL | non-functional | Control state SHALL survive restart via snapshot+WAL; links SHALL be restored revoked. | `test_resilience.Durability.test_fabric_restart_reconstructs_and_revokes_links` | release-blocking | UNASSIGNED |
| REQ-AUD-01 | SHALL | security | Every operation SHALL be recorded in a tamper-evident ledger. | `test_resilience.Ledger.test_detects_modification_deletion_reorder_truncation` | release-blocking | UNASSIGNED |
| REQ-CFG-01 | SHALL | security | Configuration SHALL be schema-validated with secure defaults; overlays SHALL NOT weaken protected fields. | `test_config_observability.Overlays.test_lower_trust_cannot_weaken` | release-blocking | UNASSIGNED |
| REQ-CFG-02 | SHALL | functional | Configuration activation SHALL be two-phase with monotonic generations and automatic rollback. | `test_config_observability.Activation.test_commit_failure_rolls_back_compensating` | release-blocking | UNASSIGNED |
| REQ-SEC-01 | SHALL | security | Secrets SHALL be referenced, never embedded, and never serialized to logs/errors. | `test_config_observability.Secrets.test_acl_cache_rotate` | release-blocking | UNASSIGNED |
| REQ-OBS-01 | SHALL | non-functional | Metrics SHALL NOT use identity labels and SHALL be cardinality bounded. | `test_config_observability.Telemetry.test_metrics_cardinality_guard` | release-blocking | UNASSIGNED |
| REQ-OBS-02 | SHALL | non-functional | Trace context SHALL propagate from caller through placement decisions. | `test_config_observability.Telemetry.test_trace_propagates_through_fabric` | release-blocking | UNASSIGNED |
| REQ-IF-01 | SHALL | interface | Wire requests SHALL validate against versioned schemas; unknown fields SHALL be rejected. | `test_semantics.Interfaces.test_fixtures_python` | release-blocking | UNASSIGNED |
| REQ-IF-02 | SHALL | interface | Version negotiation SHALL fail explicitly rather than downgrade below the minimum. | `test_semantics.Negotiation.test_minimum_enforced_downgrade` | release-blocking | UNASSIGNED |
| REQ-EXE-01 | SHALL | security | Guest execution SHALL have no ambient imports, a memory ceiling and a time limit. | `test_config_observability.WasmExecution.test_sandbox_refusals` | release-blocking | UNASSIGNED |
| REQ-CTL-01 | SHALL | functional | Operators SHALL be able to quarantine a component or host and freeze mutations immediately. | `test_resilience.EmergencyControls.test_quarantine_component` | release-blocking | UNASSIGNED |
| REQ-PERF-01 | SHOULD | non-functional | Reference control-plane overhead per capability-checked call SHOULD be p99 < 3 ms on reference hardware. | `test_governance.Bench.test_bench_baseline_present` | advisory | UNASSIGNED |
| REQ-FO-01 | SHALL | non-functional | Components on a lost host SHALL be running elsewhere within 10 s of loss declaration (non-edge classes). | `test_resilience.Placement.test_residency_aware_failover` | release-blocking | UNASSIGNED |
| REQ-EDGE-01 | MAY | functional | Edge/disconnected overlays MAY extend detector thresholds; they are then excluded from the failover SLO. | `test_config_observability.Overlays.test_every_shipped_overlay_renders` | advisory | UNASSIGNED |
| REQ-PROD-01 | SHALL | functional | Production execution SHALL use the pinned wasmCloud lattice; until present the adapter SHALL fail closed. | `test_config_observability.WasmExecution.test_abi_validation_and_wasmcloud_fails_closed` | release-blocking | UNASSIGNED |

**Prohibited states:** component running from unverified bytes; two lease holders with unexpired leases; link usable after revocation; secret value in config, log, error or ledger

**Control plane:** membership, placement, lifecycle, links, config — may depend on identity/policy/quorum.  **Data plane:** call routing — may continue in isolated_serving without the control plane.

**Non-goals:** declaring deployments; implementing providers; signing artifacts
