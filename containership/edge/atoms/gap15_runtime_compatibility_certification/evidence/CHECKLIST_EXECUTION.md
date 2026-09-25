# GAP-15 Missing-Components Checklist — Execution Record

Generated 2026-09-22 23:02 UTC by `tools/run_checklist.py`; build digest `sha256:7503b7f92eb2276a96079a1b22e1d1602a419b7a1341f9a84b77e569ef21654a`.

**Tests:** 215 run, 207 passed, 0 failed, 8 skipped (14.66s). **Exit gate:** NO_GO.

| Status | Controls |
|---|---|
| LOCALLY_VERIFIED | 541 |
| ARTIFACT_PRESENT_UNREVIEWED | 121 |
| PARTIAL | 33 |
| BLOCKED | 294 |
| NOT_APPLICABLE | 38 |
| NOT_IMPLEMENTED | 13 |
| FAILED | 0 |

Total: 1040 controls (1,020 component controls + 10 global + 10 sign-off).

LOCALLY_VERIFIED means a behaviour test tagged to the control passed in this build environment. It is not a production certification and not an independent review.

## Per component

| # | Component | Pri | Verified | Artifact | Partial | Blocked | N/A | Not impl. |
|---|---|---|---|---|---|---|---|---|
| GLOBAL | Global completion gates | P0 | 0 | 0 | 0 | 10 | 0 | 0 |
| 01 | Durable compatibility-matrix store | P0 | 13 | 2 | 1 | 4 | 0 | 0 |
| 02 | Append-only certification evidence ledger | P0 | 14 | 2 | 0 | 4 | 0 | 0 |
| 03 | Cryptographic evidence signing and verification | P0 | 13 | 2 | 0 | 5 | 0 | 0 |
| 04 | Artifact provenance binding | P0 | 12 | 2 | 0 | 6 | 0 | 0 |
| 05 | Node identity and attestation binding | P0 | 13 | 2 | 0 | 5 | 0 | 0 |
| 06 | Trusted time / clock-skew policy | P0 | 13 | 2 | 0 | 5 | 0 | 0 |
| 07 | Authentication layer | P0 | 14 | 2 | 0 | 4 | 0 | 0 |
| 08 | Authorization/capability policy | P0 | 14 | 2 | 0 | 4 | 0 | 0 |
| 09 | Schema definitions and validators | P0 | 14 | 2 | 0 | 4 | 0 | 0 |
| 10 | Evidence-ingestion boundary | P0 | 14 | 2 | 0 | 4 | 0 | 0 |
| 11 | Cross-process concurrency control | P0 | 13 | 2 | 0 | 5 | 0 | 0 |
| 12 | Tamper-evident security audit stream | P0 | 12 | 2 | 0 | 6 | 0 | 0 |
| 13 | Revocation/quarantine subsystem | P0 | 13 | 2 | 1 | 4 | 0 | 0 |
| 14 | Production service/API host | P0 | 11 | 3 | 2 | 4 | 0 | 0 |
| 15 | State recovery and disaster procedures | P0 | 6 | 2 | 4 | 7 | 0 | 1 |
| 16 | WASI/WIT/component/runtime negotiation engine | P1 | 12 | 2 | 1 | 4 | 0 | 1 |
| 17 | Typed runtime capability model | P1 | 12 | 2 | 1 | 4 | 0 | 1 |
| 18 | Version/range compatibility policy | P1 | 12 | 2 | 1 | 4 | 0 | 1 |
| 19 | Feature-subset certification model | P1 | 12 | 2 | 1 | 4 | 0 | 1 |
| 20 | Lifecycle metadata model | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 21 | Negative-evidence ageing policy | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 22 | Automatic recertification scheduler | P1 | 11 | 2 | 2 | 4 | 0 | 1 |
| 23 | Policy-precedence engine | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 24 | Offline/disconnected decision cache | P1 | 12 | 2 | 1 | 4 | 0 | 1 |
| 25 | Environment/site partition enforcement | P1 | 13 | 3 | 0 | 4 | 0 | 0 |
| 26 | Metrics exporter | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 27 | Structured logging and distributed tracing | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 28 | Operator explain endpoint/UI | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 29 | Alerting/dashboard pack | P1 | 10 | 2 | 1 | 6 | 0 | 1 |
| 30 | Admission-control integration | P1 | 12 | 2 | 0 | 6 | 0 | 0 |
| 31 | Conflict-resolution workflow | P1 | 12 | 2 | 1 | 4 | 0 | 1 |
| 32 | Capacity and resource controls | P1 | 14 | 2 | 0 | 4 | 0 | 0 |
| 33 | Real adjacent-layer integration tests | P2 | 1 | 2 | 1 | 14 | 2 | 0 |
| 34 | Runtime compatibility test matrix/fixtures | P2 | 11 | 2 | 0 | 5 | 2 | 0 |
| 35 | Parser/schema fuzzing suite | P2 | 8 | 2 | 2 | 6 | 2 | 0 |
| 36 | Security/adversarial suite | P2 | 9 | 2 | 1 | 6 | 2 | 0 |
| 37 | Concurrency/race suite | P2 | 11 | 2 | 0 | 5 | 2 | 0 |
| 38 | Fault-injection and disaster suite | P2 | 7 | 2 | 1 | 8 | 2 | 0 |
| 39 | Benchmark/soak/fleet-scale suite | P2 | 9 | 2 | 0 | 7 | 2 | 0 |
| 40 | Release acceptance evidence bundle | P2 | 7 | 2 | 1 | 8 | 2 | 0 |
| 41 | Requirements traceability matrix artifact | P2 | 10 | 2 | 1 | 5 | 2 | 0 |
| 42 | Architecture Decision Record | P2 | 0 | 9 | 1 | 7 | 2 | 1 |
| 43 | Accountable owner/escalation metadata | P2 | 2 | 2 | 1 | 12 | 2 | 1 |
| 44 | Deployment/bootstrap artifacts | P2 | 10 | 3 | 1 | 4 | 2 | 0 |
| 45 | Supply-chain artifacts | P2 | 8 | 2 | 1 | 7 | 2 | 0 |
| 46 | Canary/staged rollout and emergency-disable automation | P2 | 9 | 2 | 1 | 6 | 2 | 0 |
| 47 | Backup/restore/migration tooling | P2 | 7 | 3 | 2 | 6 | 2 | 0 |
| 48 | Operational runbooks | P2 | 1 | 10 | 1 | 5 | 2 | 1 |
| 49 | Exception/waiver registry | P2 | 12 | 2 | 0 | 4 | 2 | 0 |
| 50 | Formal production exit-gate implementation | P2 | 8 | 2 | 1 | 6 | 2 | 1 |
| 51 | Original source MASTER.md | P2 | 6 | 2 | 0 | 10 | 2 | 0 |
| SIGNOFF | Final production-readiness sign-off | P0 | 0 | 0 | 0 | 10 | 0 | 0 |

## Gate decision

```json
{
 "decision": "NO_GO",
 "inputs": {
  "tests": "PASS",
  "rtm": "FAILED",
  "sbom": "PASS",
  "provenance": "PASS",
  "security": "MISSING",
  "performance": "PASS",
  "restore": "PASS",
  "dr": "MISSING",
  "review": "MISSING",
  "approval": "MISSING"
 },
 "blockers": [
  "rtm: status 'fail'",
  "security: no evidence supplied",
  "dr: no evidence supplied",
  "review: no evidence supplied",
  "approval: no evidence supplied"
 ]
}
```

## Every control

| Control | Status | Evidence / blocker |
|---|---|---|
| GAP15-GLOBAL-001 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-002 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-003 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-004 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-005 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-006 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-007 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-008 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-009 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-GLOBAL-010 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-01-01 | LOCALLY_VERIFIED | test_persistence_model_columns |
| GAP15-MC-01-02 | LOCALLY_VERIFIED | test_engine_settings_wal_full_sync |
| GAP15-MC-01-03 | LOCALLY_VERIFIED | test_cas_rejects_lost_update |
| GAP15-MC-01-04 | LOCALLY_VERIFIED | test_indexed_historical_lookup_uses_partition_leading_index, test_persistence_model_columns |
| GAP15-MC-01-05 | LOCALLY_VERIFIED | test_atomic_commit_fault_at_every_stage_leaves_no_partial_state |
| GAP15-MC-01-06 | LOCALLY_VERIFIED | test_forward_only_migration_and_downgrade_refusal |
| GAP15-MC-01-07 | LOCALLY_VERIFIED | test_disk_full_style_io_failure_fails_closed, test_engine_settings_wal_full_sync, test_interrupted_migration_rolls_back, test_process_kill_mid_transaction_recovers |
| GAP15-MC-01-08 | PARTIAL | encryption at rest of backups needs an HSM/KMS/TPM key provider (none available to this build); scheduled restore drills need a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-01-09 | LOCALLY_VERIFIED | test_indexed_historical_lookup_uses_partition_leading_index |
| GAP15-MC-01-10 | LOCALLY_VERIFIED | test_retention_keeps_history_hot_table_bounded |
| GAP15-MC-01-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-01-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-01-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-01-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_backup_manifest_and_restore_to_staging, test_atomic_commit_fault_at_every_stage_leaves_no_partial_state |
| GAP15-MC-01-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-01-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-01-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-01-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-01-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-01-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-02-01 | LOCALLY_VERIFIED | test_happy_path_commits_everything_atomically |
| GAP15-MC-02-02 | LOCALLY_VERIFIED | test_append_only_enforced_by_database |
| GAP15-MC-02-03 | LOCALLY_VERIFIED | test_hash_chain_detects_tamper_reorder_truncate |
| GAP15-MC-02-04 | LOCALLY_VERIFIED | test_deterministic_historical_reconstruction |
| GAP15-MC-02-05 | LOCALLY_VERIFIED | test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_idempotency_key_unique_per_partition |
| GAP15-MC-02-06 | LOCALLY_VERIFIED | test_canonical_bytes_stored |
| GAP15-MC-02-07 | LOCALLY_VERIFIED | test_export_and_signed_checkpoint_offline_verifiable |
| GAP15-MC-02-08 | LOCALLY_VERIFIED | test_export_and_signed_checkpoint_offline_verifiable, test_lineage_query_by_signer_and_result |
| GAP15-MC-02-09 | LOCALLY_VERIFIED | test_retention_keeps_history_hot_table_bounded |
| GAP15-MC-02-10 | LOCALLY_VERIFIED | test_hash_chain_detects_tamper_reorder_truncate, test_reordered_duplicated_stream_rejected_by_replay |
| GAP15-MC-02-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-02-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-02-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-02-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_happy_path_commits_everything_atomically |
| GAP15-MC-02-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-02-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-02-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-02-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-02-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-02-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-03-01 | LOCALLY_VERIFIED | test_domain_separation_prevents_cross_type_and_env_replay |
| GAP15-MC-03-02 | LOCALLY_VERIFIED | test_rfc8032_vector_and_strict_s |
| GAP15-MC-03-03 | LOCALLY_VERIFIED | test_binding_fields_and_stable_reason_codes |
| GAP15-MC-03-04 | LOCALLY_VERIFIED | test_binding_fields_and_stable_reason_codes |
| GAP15-MC-03-05 | LOCALLY_VERIFIED | test_rotation_overlap_and_compromise |
| GAP15-MC-03-06 | LOCALLY_VERIFIED | test_key_id_confusion_and_signer_authorization |
| GAP15-MC-03-07 | BLOCKED | an HSM/KMS/TPM key provider (none available to this build) |
| GAP15-MC-03-08 | LOCALLY_VERIFIED | test_export_and_signed_checkpoint_offline_verifiable, test_offline_trust_bundle_roundtrip |
| GAP15-MC-03-09 | LOCALLY_VERIFIED | test_rfc8032_vector_and_strict_s |
| GAP15-MC-03-10 | LOCALLY_VERIFIED | test_binding_fields_and_stable_reason_codes |
| GAP15-MC-03-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-03-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-03-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-03-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_export_and_signed_checkpoint_offline_verifiable, test_binding_fields_and_stable_reason_codes |
| GAP15-MC-03-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-03-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-03-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-03-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-03-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-03-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-04-01 | LOCALLY_VERIFIED | test_digest_identity_required |
| GAP15-MC-04-02 | BLOCKED | the real GAP-07 provenance/signing service and builder trust roots (local verifier implemented against the same envelope shape) |
| GAP15-MC-04-03 | LOCALLY_VERIFIED | test_sbom_subject_and_unknown_fields |
| GAP15-MC-04-04 | LOCALLY_VERIFIED | test_sbom_subject_and_unknown_fields |
| GAP15-MC-04-05 | LOCALLY_VERIFIED | test_valid_and_forged_provenance |
| GAP15-MC-04-06 | LOCALLY_VERIFIED | test_multi_artifact_index_children |
| GAP15-MC-04-07 | LOCALLY_VERIFIED | test_revoked_builder_and_source |
| GAP15-MC-04-08 | LOCALLY_VERIFIED | test_tag_resolution_and_toctou |
| GAP15-MC-04-09 | BLOCKED | deployment-record correlation needs version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers |
| GAP15-MC-04-10 | LOCALLY_VERIFIED | test_valid_and_forged_provenance |
| GAP15-MC-04-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-04-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-04-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-04-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_digest_identity_required, test_multi_artifact_index_children |
| GAP15-MC-04-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-04-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-04-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-04-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-04-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-04-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-05-01 | LOCALLY_VERIFIED | test_valid_quote_derives_profile |
| GAP15-MC-05-02 | BLOCKED | the real GAP-02 device-identity/attestation service and its quote formats (TPM2/SEV-SNP/TDX) (local quote verifier implemented) |
| GAP15-MC-05-03 | LOCALLY_VERIFIED | test_valid_quote_derives_profile |
| GAP15-MC-05-04 | LOCALLY_VERIFIED | test_replay_nonce_stale_measurements_firmware |
| GAP15-MC-05-05 | LOCALLY_VERIFIED | test_replay_nonce_stale_measurements_firmware |
| GAP15-MC-05-06 | LOCALLY_VERIFIED | test_reduced_trust_policy_explicit |
| GAP15-MC-05-07 | LOCALLY_VERIFIED | test_nested_layers_and_revoked_firmware |
| GAP15-MC-05-08 | LOCALLY_VERIFIED | test_nested_layers_and_revoked_firmware |
| GAP15-MC-05-09 | LOCALLY_VERIFIED | test_node_ids_hashed_in_logs |
| GAP15-MC-05-10 | LOCALLY_VERIFIED | test_cloned_identity_and_untrusted_root, test_replay_nonce_stale_measurements_firmware |
| GAP15-MC-05-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-05-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-05-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-05-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_cloned_identity_and_untrusted_root, test_nested_layers_and_revoked_firmware |
| GAP15-MC-05-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-05-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-05-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-05-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-05-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-05-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-06-01 | BLOCKED | authenticated time sources (NTS/PTP/GPS clients) on the target hosts (source abstraction and trust ranking implemented) |
| GAP15-MC-06-02 | LOCALLY_VERIFIED | test_sources_confidence_and_skew |
| GAP15-MC-06-03 | LOCALLY_VERIFIED | test_monotonic_holdover_and_offline_grace |
| GAP15-MC-06-04 | LOCALLY_VERIFIED | test_sources_confidence_and_skew, test_untrusted_time_blocks_decisions |
| GAP15-MC-06-05 | LOCALLY_VERIFIED | test_rollback_and_forward_jump_detection |
| GAP15-MC-06-06 | LOCALLY_VERIFIED | test_monotonic_holdover_and_offline_grace |
| GAP15-MC-06-07 | LOCALLY_VERIFIED | test_times_persisted_separately |
| GAP15-MC-06-08 | LOCALLY_VERIFIED | test_monotonic_holdover_and_offline_grace |
| GAP15-MC-06-09 | LOCALLY_VERIFIED | test_sources_confidence_and_skew |
| GAP15-MC-06-10 | LOCALLY_VERIFIED | test_rollback_and_forward_jump_detection |
| GAP15-MC-06-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-06-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-06-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-06-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_monotonic_holdover_and_offline_grace, test_rollback_and_forward_jump_detection |
| GAP15-MC-06-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-06-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-06-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-06-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-06-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-06-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-07-01 | LOCALLY_VERIFIED | test_valid_token_and_typed_principal |
| GAP15-MC-07-02 | LOCALLY_VERIFIED | test_valid_token_and_typed_principal |
| GAP15-MC-07-03 | LOCALLY_VERIFIED | test_expired_wrong_audience_replay_revoked, test_valid_token_and_typed_principal |
| GAP15-MC-07-04 | LOCALLY_VERIFIED | test_expired_wrong_audience_replay_revoked, test_stale_revocation_list_fails_closed |
| GAP15-MC-07-05 | LOCALLY_VERIFIED | test_throttle_and_no_enumeration_detail |
| GAP15-MC-07-06 | LOCALLY_VERIFIED | test_channel_binding_and_node_attestation |
| GAP15-MC-07-07 | LOCALLY_VERIFIED | test_breakglass_requires_incident_and_other_approver |
| GAP15-MC-07-08 | LOCALLY_VERIFIED | test_delegation_chain_propagates |
| GAP15-MC-07-09 | LOCALLY_VERIFIED | test_secrets_not_in_logs |
| GAP15-MC-07-10 | LOCALLY_VERIFIED | test_expired_wrong_audience_replay_revoked, test_forged_token_signature_and_lifetime |
| GAP15-MC-07-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-07-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-07-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-07-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_breakglass_requires_incident_and_other_approver, test_channel_binding_and_node_attestation |
| GAP15-MC-07-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-07-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-07-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-07-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-07-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-07-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-08-01 | LOCALLY_VERIFIED | test_default_deny_and_explicit_permissions |
| GAP15-MC-08-02 | LOCALLY_VERIFIED | test_default_deny_and_explicit_permissions |
| GAP15-MC-08-03 | LOCALLY_VERIFIED | test_default_deny_and_explicit_permissions |
| GAP15-MC-08-04 | LOCALLY_VERIFIED | test_default_deny_and_explicit_permissions, test_entry_points_enforce_authorization |
| GAP15-MC-08-05 | LOCALLY_VERIFIED | test_separation_of_duties |
| GAP15-MC-08-06 | LOCALLY_VERIFIED | test_entry_points_enforce_authorization |
| GAP15-MC-08-07 | LOCALLY_VERIFIED | test_policy_bundles_signed_and_verified_before_activation, test_policy_versioning_validation_and_rollback |
| GAP15-MC-08-08 | LOCALLY_VERIFIED | test_breakglass_requires_incident_and_other_approver |
| GAP15-MC-08-09 | LOCALLY_VERIFIED | test_policy_versioning_validation_and_rollback |
| GAP15-MC-08-10 | LOCALLY_VERIFIED | test_horizontal_site_escape |
| GAP15-MC-08-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-08-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-08-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-08-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_policy_bundles_signed_and_verified_before_activation, test_hooks_observed, test_breakglass_requires_incident_and_other_approver |
| GAP15-MC-08-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-08-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-08-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-08-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-08-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-08-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-09-01 | LOCALLY_VERIFIED | test_published_schemas_match_runtime_validator |
| GAP15-MC-09-02 | LOCALLY_VERIFIED | test_published_schemas_match_runtime_validator |
| GAP15-MC-09-03 | LOCALLY_VERIFIED | test_semantic_cross_field_invariants |
| GAP15-MC-09-04 | LOCALLY_VERIFIED | test_unknown_duplicate_null_unicode_numbers |
| GAP15-MC-09-05 | LOCALLY_VERIFIED | test_versioning_and_breaking_change_diff |
| GAP15-MC-09-06 | LOCALLY_VERIFIED | test_published_schemas_match_runtime_validator |
| GAP15-MC-09-07 | LOCALLY_VERIFIED | test_unknown_duplicate_null_unicode_numbers |
| GAP15-MC-09-08 | LOCALLY_VERIFIED | test_conformance_fixtures_valid_and_invalid |
| GAP15-MC-09-09 | LOCALLY_VERIFIED | test_mutation_fuzz_parser_and_validator_fail_closed |
| GAP15-MC-09-10 | LOCALLY_VERIFIED | test_versioning_and_breaking_change_diff |
| GAP15-MC-09-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-09-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-09-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-09-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_mutation_fuzz_parser_and_validator_fail_closed, test_conformance_fixtures_valid_and_invalid |
| GAP15-MC-09-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-09-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-09-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-09-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-09-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-09-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-10-01 | LOCALLY_VERIFIED | test_happy_path_commits_everything_atomically |
| GAP15-MC-10-02 | LOCALLY_VERIFIED | test_rejections_have_stable_categories |
| GAP15-MC-10-03 | LOCALLY_VERIFIED | test_happy_path_commits_everything_atomically |
| GAP15-MC-10-04 | LOCALLY_VERIFIED | test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_idempotency_key_unique_per_partition |
| GAP15-MC-10-05 | LOCALLY_VERIFIED | test_happy_path_commits_everything_atomically, test_atomic_commit_fault_at_every_stage_leaves_no_partial_state |
| GAP15-MC-10-06 | LOCALLY_VERIFIED | test_backpressure_rate_limit_and_overload |
| GAP15-MC-10-07 | LOCALLY_VERIFIED | test_rejections_have_stable_categories |
| GAP15-MC-10-08 | LOCALLY_VERIFIED | test_rejection_forensics_without_raw_payload |
| GAP15-MC-10-09 | LOCALLY_VERIFIED | test_batch_all_or_nothing_with_per_item_status |
| GAP15-MC-10-10 | LOCALLY_VERIFIED | test_body_limits_content_type_and_encoding, test_dependency_outage_and_retry_after_crash |
| GAP15-MC-10-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-10-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-10-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-10-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_body_limits_content_type_and_encoding, test_backpressure_rate_limit_and_overload |
| GAP15-MC-10-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-10-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-10-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-10-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-10-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-10-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-11-01 | LOCALLY_VERIFIED | test_cas_rejects_lost_update |
| GAP15-MC-11-02 | LOCALLY_VERIFIED | test_parallel_writers_no_lost_updates_or_dup_seq, test_two_processes_cas_across_connections, test_cas_rejects_lost_update |
| GAP15-MC-11-03 | LOCALLY_VERIFIED | test_parallel_writers_no_lost_updates_or_dup_seq, test_revocation_vs_certify_race_revocation_wins |
| GAP15-MC-11-04 | LOCALLY_VERIFIED | test_cas_rejects_lost_update |
| GAP15-MC-11-05 | LOCALLY_VERIFIED | test_bounded_backoff_with_jitter_and_budget |
| GAP15-MC-11-06 | LOCALLY_VERIFIED | test_snapshot_reads_expose_revision, test_two_processes_cas_across_connections |
| GAP15-MC-11-07 | BLOCKED | a replicated store (multi-node) — ADR-001 records single-node SQLite only |
| GAP15-MC-11-08 | LOCALLY_VERIFIED | test_conflict_emits_structured_event |
| GAP15-MC-11-09 | LOCALLY_VERIFIED | test_parallel_writers_no_lost_updates_or_dup_seq |
| GAP15-MC-11-10 | LOCALLY_VERIFIED | test_parallel_writers_no_lost_updates_or_dup_seq, test_revocation_vs_certify_race_revocation_wins |
| GAP15-MC-11-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-11-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-11-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-11-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_parallel_writers_no_lost_updates_or_dup_seq, test_revocation_vs_certify_race_revocation_wins |
| GAP15-MC-11-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-11-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-11-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-11-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-11-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-11-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-12-01 | LOCALLY_VERIFIED | test_audit_captures_security_actions_and_redacts |
| GAP15-MC-12-02 | LOCALLY_VERIFIED | test_audit_captures_security_actions_and_redacts |
| GAP15-MC-12-03 | LOCALLY_VERIFIED | test_append_only_enforced_by_database |
| GAP15-MC-12-04 | LOCALLY_VERIFIED | test_audit_captures_security_actions_and_redacts |
| GAP15-MC-12-05 | BLOCKED | file-system access control and dual control over the store files are deployment-owned (named owners, on-call rotation and approvers) |
| GAP15-MC-12-06 | LOCALLY_VERIFIED | test_rejection_forensics_without_raw_payload, test_audit_captures_security_actions_and_redacts |
| GAP15-MC-12-07 | LOCALLY_VERIFIED | test_audit_chain_independent_export, test_export_and_signed_checkpoint_offline_verifiable |
| GAP15-MC-12-08 | LOCALLY_VERIFIED | test_hash_chain_detects_tamper_reorder_truncate |
| GAP15-MC-12-09 | BLOCKED | an external SIEM/SOC pipeline |
| GAP15-MC-12-10 | LOCALLY_VERIFIED | test_hash_chain_detects_tamper_reorder_truncate |
| GAP15-MC-12-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-12-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-12-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-12-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_rejection_forensics_without_raw_payload, test_audit_captures_security_actions_and_redacts |
| GAP15-MC-12-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-12-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-12-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-12-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-12-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-12-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-13-01 | LOCALLY_VERIFIED | test_revocation_overrides_valid_evidence_and_history_kept |
| GAP15-MC-13-02 | LOCALLY_VERIFIED | test_revocation_overrides_valid_evidence_and_history_kept |
| GAP15-MC-13-03 | PARTIAL | propagation to remote admission caches needs a fleet/lab estate, real hardware profiles and a production-like deployment; offline bundles carry a revocation-checkpoint freshness bound |
| GAP15-MC-13-04 | LOCALLY_VERIFIED | test_revocation_overrides_valid_evidence_and_history_kept, test_revocation_vs_certify_race_revocation_wins |
| GAP15-MC-13-05 | LOCALLY_VERIFIED | test_quarantine_distinct_and_expiring |
| GAP15-MC-13-06 | LOCALLY_VERIFIED | test_revocation_overrides_valid_evidence_and_history_kept |
| GAP15-MC-13-07 | LOCALLY_VERIFIED | test_signer_compromise_enumerates_affected_evidence, test_rotation_overlap_and_compromise |
| GAP15-MC-13-08 | LOCALLY_VERIFIED | test_bulk_revocation_requires_preview_and_guard |
| GAP15-MC-13-09 | LOCALLY_VERIFIED | test_revocation_audit_and_restore_preserves_it |
| GAP15-MC-13-10 | LOCALLY_VERIFIED | test_revocation_audit_and_restore_preserves_it |
| GAP15-MC-13-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-13-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-13-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-13-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_bulk_revocation_requires_preview_and_guard, test_quarantine_distinct_and_expiring |
| GAP15-MC-13-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-13-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-13-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-13-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-13-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-13-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-14-01 | LOCALLY_VERIFIED | test_contract_routes_and_error_codes |
| GAP15-MC-14-02 | LOCALLY_VERIFIED | test_body_limits_content_type_and_encoding, test_concurrency_gate_sheds |
| GAP15-MC-14-03 | LOCALLY_VERIFIED | test_health_ready_metrics_protected |
| GAP15-MC-14-04 | LOCALLY_VERIFIED | test_graceful_shutdown_drains_and_readiness_flips |
| GAP15-MC-14-05 | LOCALLY_VERIFIED | test_contract_routes_and_error_codes, test_rejections_have_stable_categories |
| GAP15-MC-14-06 | LOCALLY_VERIFIED | test_body_limits_content_type_and_encoding |
| GAP15-MC-14-07 | PARTIAL | TLS policy context implemented; certificates and rotation need deployment-issued TLS certificates and a rotation mechanism |
| GAP15-MC-14-08 | LOCALLY_VERIFIED | test_contract_routes_and_error_codes |
| GAP15-MC-14-09 | LOCALLY_VERIFIED | test_health_ready_metrics_protected |
| GAP15-MC-14-10 | ARTIFACT_PRESENT_UNREVIEWED | test_deployment_manifests_least_privilege |
| GAP15-MC-14-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-14-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-14-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-14-14 | PARTIAL | no test tagged to the component's adversarial/negative item 14-10 |
| GAP15-MC-14-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-14-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-14-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-14-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-14-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-14-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-15-01 | LOCALLY_VERIFIED | test_measured_rpo_rto |
| GAP15-MC-15-02 | PARTIAL | signed + hashed backups implemented; encryption/key recovery/geo separation need an HSM/KMS/TPM key provider (none available to this build) |
| GAP15-MC-15-03 | LOCALLY_VERIFIED | test_process_kill_mid_transaction_recovers |
| GAP15-MC-15-04 | BLOCKED | a replicated store (multi-node) — ADR-001 records single-node SQLite only |
| GAP15-MC-15-05 | LOCALLY_VERIFIED | test_backup_manifest_and_restore_to_staging |
| GAP15-MC-15-06 | LOCALLY_VERIFIED | test_restore_refuses_corrupt_forged_and_existing_target, test_forward_only_migration_and_downgrade_refusal |
| GAP15-MC-15-07 | LOCALLY_VERIFIED | test_untrusted_time_blocks_decisions |
| GAP15-MC-15-08 | BLOCKED | failover/failback automation needs a replicated store (multi-node) — ADR-001 records single-node SQLite only |
| GAP15-MC-15-09 | PARTIAL | one measured restore (RPO/RTO) recorded; scheduled drills need a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-15-10 | BLOCKED | signed DR report needs an authorised release identity to sign GO decisions |
| GAP15-MC-15-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-15-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-15-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-15-14 | PARTIAL | no test tagged to the component's adversarial/negative item 15-10 |
| GAP15-MC-15-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-15-16 | PARTIAL | unresolved rows: GAP15-MC-15-12 |
| GAP15-MC-15-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-15-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-15-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-15-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-16-01 | LOCALLY_VERIFIED | test_fit_transcript_and_determinism |
| GAP15-MC-16-02 | LOCALLY_VERIFIED | test_aliases_normalised_ambiguous_rejected |
| GAP15-MC-16-03 | LOCALLY_VERIFIED | test_fit_transcript_and_determinism, test_rejections_version_gap_missing_interface_forbidden |
| GAP15-MC-16-04 | LOCALLY_VERIFIED | test_shims_only_explicit_and_trusted |
| GAP15-MC-16-05 | LOCALLY_VERIFIED | test_fit_transcript_and_determinism |
| GAP15-MC-16-06 | LOCALLY_VERIFIED | test_fit_transcript_and_determinism |
| GAP15-MC-16-07 | LOCALLY_VERIFIED | test_precedence_revocation_lifecycle_policy |
| GAP15-MC-16-08 | LOCALLY_VERIFIED | test_experimental_needs_opt_in |
| GAP15-MC-16-09 | LOCALLY_VERIFIED | test_rejections_version_gap_missing_interface_forbidden |
| GAP15-MC-16-10 | LOCALLY_VERIFIED | test_cardinality_bound_and_benchmark |
| GAP15-MC-16-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-16-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-16-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-16-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_aliases_normalised_ambiguous_rejected, test_cardinality_bound_and_benchmark, test_experimental_needs_opt_in |
| GAP15-MC-16-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-16-16 | PARTIAL | unresolved rows: GAP15-MC-16-12 |
| GAP15-MC-16-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-16-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-16-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-16-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-17-01 | LOCALLY_VERIFIED | test_typed_layers_provenance_and_identity |
| GAP15-MC-17-02 | LOCALLY_VERIFIED | test_typed_layers_provenance_and_identity |
| GAP15-MC-17-03 | LOCALLY_VERIFIED | test_unknown_core_values_and_extensions |
| GAP15-MC-17-04 | LOCALLY_VERIFIED | test_valid_quote_derives_profile, test_typed_layers_provenance_and_identity |
| GAP15-MC-17-05 | LOCALLY_VERIFIED | test_parameterised_capabilities_and_unknown_state |
| GAP15-MC-17-06 | LOCALLY_VERIFIED | test_aliases_normalised_ambiguous_rejected |
| GAP15-MC-17-07 | LOCALLY_VERIFIED | test_typed_layers_provenance_and_identity |
| GAP15-MC-17-08 | LOCALLY_VERIFIED | test_parameterised_capabilities_and_unknown_state |
| GAP15-MC-17-09 | LOCALLY_VERIFIED | test_parameterised_capabilities_and_unknown_state |
| GAP15-MC-17-10 | LOCALLY_VERIFIED | test_unknown_core_values_and_extensions |
| GAP15-MC-17-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-17-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-17-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-17-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_valid_quote_derives_profile, test_parameterised_capabilities_and_unknown_state, test_typed_layers_provenance_and_identity |
| GAP15-MC-17-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-17-16 | PARTIAL | unresolved rows: GAP15-MC-17-12 |
| GAP15-MC-17-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-17-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-17-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-17-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-18-01 | LOCALLY_VERIFIED | test_namespaces_and_semver_rules |
| GAP15-MC-18-02 | LOCALLY_VERIFIED | test_rejections_version_gap_missing_interface_forbidden, test_namespaces_and_semver_rules |
| GAP15-MC-18-03 | LOCALLY_VERIFIED | test_namespaces_and_semver_rules |
| GAP15-MC-18-04 | LOCALLY_VERIFIED | test_experimental_needs_opt_in, test_no_implicit_widening_and_exclusions |
| GAP15-MC-18-05 | LOCALLY_VERIFIED | test_no_implicit_widening_and_exclusions |
| GAP15-MC-18-06 | LOCALLY_VERIFIED | test_ruleset_revision_in_verdicts_and_canonical_ranges |
| GAP15-MC-18-07 | LOCALLY_VERIFIED | test_ruleset_revision_in_verdicts_and_canonical_ranges |
| GAP15-MC-18-08 | LOCALLY_VERIFIED | test_unsatisfiable_explained |
| GAP15-MC-18-09 | LOCALLY_VERIFIED | test_property_based_interval_boundaries |
| GAP15-MC-18-10 | LOCALLY_VERIFIED | test_rule_change_regression_report |
| GAP15-MC-18-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-18-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-18-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-18-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_experimental_needs_opt_in, test_rejections_version_gap_missing_interface_forbidden, test_namespaces_and_semver_rules |
| GAP15-MC-18-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-18-16 | PARTIAL | unresolved rows: GAP15-MC-18-12 |
| GAP15-MC-18-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-18-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-18-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-18-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-19-01 | LOCALLY_VERIFIED | test_child_pass_never_implies_parent |
| GAP15-MC-19-02 | LOCALLY_VERIFIED | test_child_pass_never_implies_parent |
| GAP15-MC-19-03 | LOCALLY_VERIFIED | test_child_pass_never_implies_parent |
| GAP15-MC-19-04 | LOCALLY_VERIFIED | test_aggregation_conflicts_and_provenance |
| GAP15-MC-19-05 | LOCALLY_VERIFIED | test_aggregation_conflicts_and_provenance |
| GAP15-MC-19-06 | LOCALLY_VERIFIED | test_aggregation_conflicts_and_provenance |
| GAP15-MC-19-07 | LOCALLY_VERIFIED | test_admission_requires_complete_feature_set_and_cache_key |
| GAP15-MC-19-08 | LOCALLY_VERIFIED | test_admission_requires_complete_feature_set_and_cache_key |
| GAP15-MC-19-09 | LOCALLY_VERIFIED | test_admission_requires_complete_feature_set_and_cache_key |
| GAP15-MC-19-10 | LOCALLY_VERIFIED | test_admission_requires_complete_feature_set_and_cache_key |
| GAP15-MC-19-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-19-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-19-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-19-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_admission_requires_complete_feature_set_and_cache_key, test_aggregation_conflicts_and_provenance, test_child_pass_never_implies_parent |
| GAP15-MC-19-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-19-16 | PARTIAL | unresolved rows: GAP15-MC-19-12 |
| GAP15-MC-19-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-19-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-19-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-19-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-20-01 | LOCALLY_VERIFIED | test_transition_graph_and_metadata |
| GAP15-MC-20-02 | LOCALLY_VERIFIED | test_transition_graph_and_metadata |
| GAP15-MC-20-03 | LOCALLY_VERIFIED | test_transition_graph_and_metadata |
| GAP15-MC-20-04 | LOCALLY_VERIFIED | test_existing_vs_new_admissions |
| GAP15-MC-20-05 | LOCALLY_VERIFIED | test_separation_of_duties, test_reactivation_needs_waiver_and_two_people |
| GAP15-MC-20-06 | LOCALLY_VERIFIED | test_future_effective_dates_and_warnings |
| GAP15-MC-20-07 | LOCALLY_VERIFIED | test_future_effective_dates_and_warnings |
| GAP15-MC-20-08 | LOCALLY_VERIFIED | test_historical_lifecycle_views_and_explain |
| GAP15-MC-20-09 | LOCALLY_VERIFIED | test_future_effective_dates_and_warnings |
| GAP15-MC-20-10 | LOCALLY_VERIFIED | test_historical_lifecycle_views_and_explain |
| GAP15-MC-20-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-20-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-20-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-20-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_separation_of_duties, test_existing_vs_new_admissions |
| GAP15-MC-20-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-20-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-20-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-20-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-20-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-20-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-21-01 | LOCALLY_VERIFIED | test_failure_classes_and_ttl_boundaries |
| GAP15-MC-21-02 | LOCALLY_VERIFIED | test_failure_classes_and_ttl_boundaries |
| GAP15-MC-21-03 | LOCALLY_VERIFIED | test_failure_classes_and_ttl_boundaries |
| GAP15-MC-21-04 | LOCALLY_VERIFIED | test_failure_classes_and_ttl_boundaries |
| GAP15-MC-21-05 | LOCALLY_VERIFIED | test_newer_positive_supersedes_with_linkage_and_producer_conflict |
| GAP15-MC-21-06 | LOCALLY_VERIFIED | test_newer_positive_supersedes_with_linkage_and_producer_conflict |
| GAP15-MC-21-07 | LOCALLY_VERIFIED | test_failure_classes_and_ttl_boundaries |
| GAP15-MC-21-08 | LOCALLY_VERIFIED | test_offline_cache_never_ages_negative_into_positive |
| GAP15-MC-21-09 | LOCALLY_VERIFIED | test_negative_metrics_visible |
| GAP15-MC-21-10 | LOCALLY_VERIFIED | test_failure_classes_and_ttl_boundaries |
| GAP15-MC-21-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-21-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-21-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-21-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_failure_classes_and_ttl_boundaries, test_negative_metrics_visible |
| GAP15-MC-21-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-21-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-21-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-21-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-21-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-21-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-22-01 | LOCALLY_VERIFIED | test_idempotent_queue_priority_and_quota |
| GAP15-MC-22-02 | PARTIAL | idempotent keyed queue implemented in memory; durable persistence of the queue is not implemented |
| GAP15-MC-22-03 | LOCALLY_VERIFIED | test_idempotent_queue_priority_and_quota |
| GAP15-MC-22-04 | LOCALLY_VERIFIED | test_idempotent_queue_priority_and_quota |
| GAP15-MC-22-05 | LOCALLY_VERIFIED | test_leases_fencing_retry_dead_letter |
| GAP15-MC-22-06 | LOCALLY_VERIFIED | test_leases_fencing_retry_dead_letter |
| GAP15-MC-22-07 | LOCALLY_VERIFIED | test_supersession_cancel_controls_and_metrics |
| GAP15-MC-22-08 | LOCALLY_VERIFIED | test_supersession_cancel_controls_and_metrics |
| GAP15-MC-22-09 | LOCALLY_VERIFIED | test_supersession_cancel_controls_and_metrics |
| GAP15-MC-22-10 | LOCALLY_VERIFIED | test_massive_expiry_storm_bounded |
| GAP15-MC-22-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-22-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-22-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-22-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_idempotent_queue_priority_and_quota, test_leases_fencing_retry_dead_letter, test_massive_expiry_storm_bounded |
| GAP15-MC-22-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-22-16 | PARTIAL | unresolved rows: GAP15-MC-22-12 |
| GAP15-MC-22-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-22-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-22-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-22-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-23-01 | LOCALLY_VERIFIED | test_precedence_and_trace |
| GAP15-MC-23-02 | LOCALLY_VERIFIED | test_precedence_and_trace |
| GAP15-MC-23-03 | LOCALLY_VERIFIED | test_waivers_scoped_non_waivable |
| GAP15-MC-23-04 | LOCALLY_VERIFIED | test_precedence_and_trace |
| GAP15-MC-23-05 | LOCALLY_VERIFIED | test_bundle_validation |
| GAP15-MC-23-06 | LOCALLY_VERIFIED | test_policy_bundles_signed_and_verified_before_activation, test_bundle_validation |
| GAP15-MC-23-07 | LOCALLY_VERIFIED | test_canary_simulation_and_unavailable_policy |
| GAP15-MC-23-08 | LOCALLY_VERIFIED | test_canary_simulation_and_unavailable_policy |
| GAP15-MC-23-09 | LOCALLY_VERIFIED | test_rule_change_regression_report |
| GAP15-MC-23-10 | LOCALLY_VERIFIED | test_canary_simulation_and_unavailable_policy |
| GAP15-MC-23-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-23-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-23-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-23-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_policy_bundles_signed_and_verified_before_activation, test_hooks_observed, test_bundle_validation |
| GAP15-MC-23-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-23-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-23-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-23-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-23-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-23-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-24-01 | LOCALLY_VERIFIED | test_signed_scoped_typed_entries |
| GAP15-MC-24-02 | LOCALLY_VERIFIED | test_signed_scoped_typed_entries |
| GAP15-MC-24-03 | LOCALLY_VERIFIED | test_hard_expiry_revocation_freshness_rollback |
| GAP15-MC-24-04 | LOCALLY_VERIFIED | test_offline_cache_never_ages_negative_into_positive, test_signed_scoped_typed_entries |
| GAP15-MC-24-05 | LOCALLY_VERIFIED | test_hard_expiry_revocation_freshness_rollback |
| GAP15-MC-24-06 | LOCALLY_VERIFIED | test_atomic_write_and_tamper |
| GAP15-MC-24-07 | LOCALLY_VERIFIED | test_deny_first_eviction |
| GAP15-MC-24-08 | LOCALLY_VERIFIED | test_reconnect_reconciliation |
| GAP15-MC-24-09 | LOCALLY_VERIFIED | test_signed_scoped_typed_entries |
| GAP15-MC-24-10 | LOCALLY_VERIFIED | test_atomic_write_and_tamper, test_hard_expiry_revocation_freshness_rollback |
| GAP15-MC-24-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-24-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-24-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-24-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_offline_cache_never_ages_negative_into_positive, test_atomic_write_and_tamper, test_deny_first_eviction |
| GAP15-MC-24-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-24-16 | PARTIAL | unresolved rows: GAP15-MC-24-12 |
| GAP15-MC-24-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-24-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-24-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-24-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-25-01 | LOCALLY_VERIFIED | test_canonical_identifiers |
| GAP15-MC-25-02 | LOCALLY_VERIFIED | test_domain_separation_prevents_cross_type_and_env_replay, test_no_cross_partition_evidence_reuse |
| GAP15-MC-25-03 | LOCALLY_VERIFIED | test_indexed_historical_lookup_uses_partition_leading_index |
| GAP15-MC-25-04 | LOCALLY_VERIFIED | test_no_cross_partition_evidence_reuse |
| GAP15-MC-25-05 | ARTIFACT_PRESENT_UNREVIEWED | test_replication_export_rules_documented |
| GAP15-MC-25-06 | LOCALLY_VERIFIED | test_restore_refuses_foreign_partition |
| GAP15-MC-25-07 | LOCALLY_VERIFIED | test_per_partition_quota_fairness |
| GAP15-MC-25-08 | LOCALLY_VERIFIED | test_partition_context_in_traces_logs |
| GAP15-MC-25-09 | LOCALLY_VERIFIED | test_horizontal_site_escape |
| GAP15-MC-25-10 | LOCALLY_VERIFIED | test_restore_refuses_foreign_partition |
| GAP15-MC-25-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-25-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-25-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-25-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_restore_refuses_foreign_partition, test_indexed_historical_lookup_uses_partition_leading_index |
| GAP15-MC-25-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-25-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-25-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-25-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-25-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-25-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-26-01 | LOCALLY_VERIFIED | test_declared_metrics_bounded_labels |
| GAP15-MC-26-02 | LOCALLY_VERIFIED | test_declared_metrics_bounded_labels, test_gauges_coverage_backlog |
| GAP15-MC-26-03 | LOCALLY_VERIFIED | test_latency_histograms_and_exposition, test_latency_throughput_envelope_recorded |
| GAP15-MC-26-04 | LOCALLY_VERIFIED | test_latency_histograms_and_exposition |
| GAP15-MC-26-05 | LOCALLY_VERIFIED | test_declared_metrics_bounded_labels |
| GAP15-MC-26-06 | LOCALLY_VERIFIED | test_declared_metrics_bounded_labels |
| GAP15-MC-26-07 | LOCALLY_VERIFIED | test_health_ready_metrics_protected |
| GAP15-MC-26-08 | LOCALLY_VERIFIED | test_latency_histograms_and_exposition |
| GAP15-MC-26-09 | LOCALLY_VERIFIED | test_metric_correctness_under_duplicates_and_restart |
| GAP15-MC-26-10 | LOCALLY_VERIFIED | test_recording_rules_exist_for_key_conditions |
| GAP15-MC-26-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-26-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-26-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-26-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_health_ready_metrics_protected, test_declared_metrics_bounded_labels |
| GAP15-MC-26-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-26-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-26-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-26-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-26-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-26-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-27-01 | LOCALLY_VERIFIED | test_structured_schema_and_injection |
| GAP15-MC-27-02 | LOCALLY_VERIFIED | test_trace_context_propagation_and_sampling |
| GAP15-MC-27-03 | LOCALLY_VERIFIED | test_trace_context_propagation_and_sampling |
| GAP15-MC-27-04 | LOCALLY_VERIFIED | test_trace_context_propagation_and_sampling |
| GAP15-MC-27-05 | LOCALLY_VERIFIED | test_secrets_not_in_logs |
| GAP15-MC-27-06 | LOCALLY_VERIFIED | test_structured_schema_and_injection |
| GAP15-MC-27-07 | LOCALLY_VERIFIED | test_audit_correlation |
| GAP15-MC-27-08 | LOCALLY_VERIFIED | test_structured_schema_and_injection |
| GAP15-MC-27-09 | LOCALLY_VERIFIED | test_node_ids_hashed_in_logs, test_retention_privacy_documented |
| GAP15-MC-27-10 | LOCALLY_VERIFIED | test_trace_context_propagation_and_sampling |
| GAP15-MC-27-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-27-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-27-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-27-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_node_ids_hashed_in_logs, test_secrets_not_in_logs |
| GAP15-MC-27-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-27-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-27-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-27-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-27-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-27-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-28-01 | LOCALLY_VERIFIED | test_explain_model_from_same_trace |
| GAP15-MC-28-02 | LOCALLY_VERIFIED | test_every_reason_code_has_remediation |
| GAP15-MC-28-03 | LOCALLY_VERIFIED | test_explain_model_from_same_trace |
| GAP15-MC-28-04 | LOCALLY_VERIFIED | test_explain_authorization_and_redaction |
| GAP15-MC-28-05 | LOCALLY_VERIFIED | test_deterministic_historical_reconstruction, test_explain_does_not_reevaluate_by_default |
| GAP15-MC-28-06 | LOCALLY_VERIFIED | test_historical_lifecycle_views_and_explain |
| GAP15-MC-28-07 | LOCALLY_VERIFIED | test_explain_model_from_same_trace |
| GAP15-MC-28-08 | LOCALLY_VERIFIED | test_explain_does_not_reevaluate_by_default |
| GAP15-MC-28-09 | LOCALLY_VERIFIED | test_large_history_paginated |
| GAP15-MC-28-10 | LOCALLY_VERIFIED | test_every_reason_code_has_remediation |
| GAP15-MC-28-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-28-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-28-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-28-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_deterministic_historical_reconstruction, test_every_reason_code_has_remediation |
| GAP15-MC-28-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-28-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-28-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-28-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-28-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-28-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-29-01 | LOCALLY_VERIFIED | test_alert_pack_owner_severity_runbook, test_pack_written |
| GAP15-MC-29-02 | LOCALLY_VERIFIED | test_recording_rules_exist_for_key_conditions |
| GAP15-MC-29-03 | LOCALLY_VERIFIED | test_alert_pack_owner_severity_runbook |
| GAP15-MC-29-04 | LOCALLY_VERIFIED | test_alert_pack_owner_severity_runbook |
| GAP15-MC-29-05 | LOCALLY_VERIFIED | test_alert_pack_owner_severity_runbook |
| GAP15-MC-29-06 | LOCALLY_VERIFIED | test_alert_pack_owner_severity_runbook, test_runbook_links_resolve |
| GAP15-MC-29-07 | LOCALLY_VERIFIED | test_silence_controls |
| GAP15-MC-29-08 | BLOCKED | threshold validation against load/fault replays needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-29-09 | LOCALLY_VERIFIED | test_alert_pipeline_watchdog |
| GAP15-MC-29-10 | BLOCKED | review cadence is a process control: named owners, on-call rotation and approvers |
| GAP15-MC-29-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-29-12 | NOT_IMPLEMENTED |  |
| GAP15-MC-29-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-29-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_alert_pack_owner_severity_runbook, test_alert_pipeline_watchdog, test_pack_written |
| GAP15-MC-29-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-29-16 | PARTIAL | unresolved rows: GAP15-MC-29-12 |
| GAP15-MC-29-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-29-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-29-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-29-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-30-01 | LOCALLY_VERIFIED | test_admission_contract_and_revision_binding |
| GAP15-MC-30-02 | LOCALLY_VERIFIED | test_admission_contract_and_revision_binding |
| GAP15-MC-30-03 | LOCALLY_VERIFIED | test_fail_closed_matrix_unsupported_expired_eol_revoked |
| GAP15-MC-30-04 | LOCALLY_VERIFIED | test_admission_contract_and_revision_binding |
| GAP15-MC-30-05 | BLOCKED | integration with GAP-08/SCH-01/PLN-04 needs version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (idempotent admission API implemented) |
| GAP15-MC-30-06 | LOCALLY_VERIFIED | test_revocation_outranks_cached_allow_and_prestart_recheck |
| GAP15-MC-30-07 | LOCALLY_VERIFIED | test_denial_reasons_safe |
| GAP15-MC-30-08 | LOCALLY_VERIFIED | test_admission_contract_and_revision_binding |
| GAP15-MC-30-09 | LOCALLY_VERIFIED | test_tag_resolution_and_toctou, test_revocation_outranks_cached_allow_and_prestart_recheck |
| GAP15-MC-30-10 | BLOCKED | every supported execution tier needs version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers |
| GAP15-MC-30-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-30-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-30-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-30-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_tag_resolution_and_toctou, test_admission_contract_and_revision_binding |
| GAP15-MC-30-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-30-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-30-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-30-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-30-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-30-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-31-01 | LOCALLY_VERIFIED | test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_case_object_and_quarantine |
| GAP15-MC-31-02 | LOCALLY_VERIFIED | test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_case_object_and_quarantine |
| GAP15-MC-31-03 | LOCALLY_VERIFIED | test_newer_positive_supersedes_with_linkage_and_producer_conflict |
| GAP15-MC-31-04 | LOCALLY_VERIFIED | test_two_person_resolution_preserves_history |
| GAP15-MC-31-05 | LOCALLY_VERIFIED | test_two_person_resolution_preserves_history |
| GAP15-MC-31-06 | LOCALLY_VERIFIED | test_case_object_and_quarantine |
| GAP15-MC-31-07 | LOCALLY_VERIFIED | test_case_object_and_quarantine |
| GAP15-MC-31-08 | NOT_IMPLEMENTED | no producer/operator notification channel exists |
| GAP15-MC-31-09 | LOCALLY_VERIFIED | test_both_invalid_quarantines_evidence |
| GAP15-MC-31-10 | LOCALLY_VERIFIED | test_both_invalid_quarantines_evidence, test_reconnect_reconciliation |
| GAP15-MC-31-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-31-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-31-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-31-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_both_invalid_quarantines_evidence |
| GAP15-MC-31-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-31-16 | PARTIAL | unresolved rows: GAP15-MC-31-08 |
| GAP15-MC-31-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-31-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-31-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-31-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-32-01 | LOCALLY_VERIFIED | test_documented_limits |
| GAP15-MC-32-02 | LOCALLY_VERIFIED | test_backpressure_rate_limit_and_overload |
| GAP15-MC-32-03 | LOCALLY_VERIFIED | test_backpressure_rate_limit_and_overload, test_concurrency_gate_sheds |
| GAP15-MC-32-04 | LOCALLY_VERIFIED | test_retention_keeps_history_hot_table_bounded |
| GAP15-MC-32-05 | LOCALLY_VERIFIED | test_indexed_historical_lookup_uses_partition_leading_index |
| GAP15-MC-32-06 | LOCALLY_VERIFIED | test_body_limits_content_type_and_encoding, test_pathological_sizes_bounded |
| GAP15-MC-32-07 | LOCALLY_VERIFIED | test_per_partition_quota_fairness |
| GAP15-MC-32-08 | LOCALLY_VERIFIED | test_priority_paths_survive_overload |
| GAP15-MC-32-09 | LOCALLY_VERIFIED | test_capacity_metrics_exported |
| GAP15-MC-32-10 | LOCALLY_VERIFIED | test_massive_expiry_storm_bounded |
| GAP15-MC-32-11 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section |
| GAP15-MC-32-12 | LOCALLY_VERIFIED | test_hooks_observed |
| GAP15-MC-32-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-32-14 | LOCALLY_VERIFIED | test_every_runtime_component_has_a_validated_config_section, test_hooks_observed, test_body_limits_content_type_and_encoding, test_pathological_sizes_bounded |
| GAP15-MC-32-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-32-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-32-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-32-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-32-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-32-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-33-01 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-02 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-03 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-04 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-05 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-06 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-07 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-08 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-09 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-10 | BLOCKED | version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers (local simulated coverage listed where tagged) |
| GAP15-MC-33-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-33-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-33-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-33-14 | PARTIAL | no test tagged to the component's adversarial/negative item 33-10 |
| GAP15-MC-33-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-33-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-33-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-33-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-33-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-33-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-34-01 | LOCALLY_VERIFIED | test_inventory_risk_based_matrix_and_gaps |
| GAP15-MC-34-02 | LOCALLY_VERIFIED | test_inventory_risk_based_matrix_and_gaps |
| GAP15-MC-34-03 | LOCALLY_VERIFIED | test_results_carry_harness_identity |
| GAP15-MC-34-04 | LOCALLY_VERIFIED | test_fixture_categories_present |
| GAP15-MC-34-05 | LOCALLY_VERIFIED | test_results_carry_harness_identity |
| GAP15-MC-34-06 | LOCALLY_VERIFIED | test_inventory_risk_based_matrix_and_gaps |
| GAP15-MC-34-07 | BLOCKED | lab/production parity needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-34-08 | LOCALLY_VERIFIED | test_results_carry_harness_identity |
| GAP15-MC-34-09 | LOCALLY_VERIFIED | test_gauges_coverage_backlog, test_inventory_risk_based_matrix_and_gaps |
| GAP15-MC-34-10 | LOCALLY_VERIFIED | test_retired_runtime_history_preserved |
| GAP15-MC-34-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-34-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-34-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-34-14 | LOCALLY_VERIFIED | test_gauges_coverage_backlog, test_fixture_categories_present, test_inventory_risk_based_matrix_and_gaps, test_results_carry_harness_identity |
| GAP15-MC-34-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-34-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-34-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-34-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-34-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-34-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-35-01 | LOCALLY_VERIFIED | test_mutation_fuzz_parser_and_validator_fail_closed |
| GAP15-MC-35-02 | PARTIAL | harness calls production parsers directly; sanitizers do not apply to pure Python |
| GAP15-MC-35-03 | LOCALLY_VERIFIED | test_unknown_duplicate_null_unicode_numbers |
| GAP15-MC-35-04 | PARTIAL | seeded mutation fuzzing implemented; coverage guidance and corpus minimisation are not |
| GAP15-MC-35-05 | LOCALLY_VERIFIED | test_mutation_fuzz_parser_and_validator_fail_closed, test_pathological_sizes_bounded |
| GAP15-MC-35-06 | LOCALLY_VERIFIED | test_canonical_differential_two_encodings_one_digest, test_rfc8032_vector_and_strict_s |
| GAP15-MC-35-07 | LOCALLY_VERIFIED | test_canonical_differential_two_encodings_one_digest |
| GAP15-MC-35-08 | BLOCKED | a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-35-09 | BLOCKED | triage SLA needs named owners, on-call rotation and approvers |
| GAP15-MC-35-10 | LOCALLY_VERIFIED | test_mutation_fuzz_parser_and_validator_fail_closed |
| GAP15-MC-35-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-35-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-35-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-35-14 | LOCALLY_VERIFIED | test_canonical_differential_two_encodings_one_digest, test_mutation_fuzz_parser_and_validator_fail_closed, test_pathological_sizes_bounded, test_unknown_duplicate_null_unicode_numbers |
| GAP15-MC-35-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-35-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-35-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-35-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-35-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-35-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-36-01 | LOCALLY_VERIFIED | test_replay_nonce_stale_measurements_firmware, test_expired_wrong_audience_replay_revoked, test_domain_separation_prevents_cross_type_and_env_replay |
| GAP15-MC-36-02 | LOCALLY_VERIFIED | test_cloned_identity_and_untrusted_root, test_channel_binding_and_node_attestation, test_digest_identity_required, test_key_id_confusion_and_signer_authorization |
| GAP15-MC-36-03 | LOCALLY_VERIFIED | test_signer_compromise_enumerates_affected_evidence, test_forged_token_signature_and_lifetime, test_rotation_overlap_and_compromise |
| GAP15-MC-36-04 | LOCALLY_VERIFIED | test_entry_points_enforce_authorization, test_release_key_cannot_sign_review |
| GAP15-MC-36-05 | LOCALLY_VERIFIED | test_sql_and_path_injection_inert |
| GAP15-MC-36-06 | LOCALLY_VERIFIED | test_pathological_sizes_bounded, test_backpressure_rate_limit_and_overload |
| GAP15-MC-36-07 | LOCALLY_VERIFIED | test_horizontal_site_escape, test_no_cross_partition_evidence_reuse |
| GAP15-MC-36-08 | LOCALLY_VERIFIED | test_stale_revocation_list_fails_closed |
| GAP15-MC-36-09 | BLOCKED | red-team exercise needs named owners, on-call rotation and approvers |
| GAP15-MC-36-10 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-36-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-36-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-36-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-36-14 | PARTIAL | no test tagged to the component's adversarial/negative item 36-10 |
| GAP15-MC-36-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-36-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-36-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-36-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-36-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-36-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-37-01 | LOCALLY_VERIFIED | test_parallel_writers_no_lost_updates_or_dup_seq |
| GAP15-MC-37-02 | LOCALLY_VERIFIED | test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_parallel_writers_no_lost_updates_or_dup_seq |
| GAP15-MC-37-03 | LOCALLY_VERIFIED | test_lifecycle_transition_races_certify_monotonic |
| GAP15-MC-37-04 | LOCALLY_VERIFIED | test_revocation_vs_certify_race_revocation_wins, test_revocation_outranks_cached_allow_and_prestart_recheck |
| GAP15-MC-37-05 | LOCALLY_VERIFIED | test_policy_swap_during_inflight_decisions_bound_to_one_revision |
| GAP15-MC-37-06 | BLOCKED | a replicated store (multi-node) — ADR-001 records single-node SQLite only |
| GAP15-MC-37-07 | LOCALLY_VERIFIED | test_backup_while_writes_active |
| GAP15-MC-37-08 | LOCALLY_VERIFIED | test_parallel_writers_no_lost_updates_or_dup_seq |
| GAP15-MC-37-09 | LOCALLY_VERIFIED | test_randomized_stress_with_seed |
| GAP15-MC-37-10 | LOCALLY_VERIFIED | test_randomized_stress_with_seed |
| GAP15-MC-37-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-37-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-37-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-37-14 | LOCALLY_VERIFIED | test_exact_retry_idempotent_conflicting_resubmission_quarantines, test_backup_while_writes_active, test_parallel_writers_no_lost_updates_or_dup_seq, test_randomized_stress_with_seed |
| GAP15-MC-37-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-37-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-37-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-37-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-37-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-37-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-38-01 | LOCALLY_VERIFIED | test_atomic_commit_fault_at_every_stage_leaves_no_partial_state, test_process_kill_mid_transaction_recovers |
| GAP15-MC-38-02 | LOCALLY_VERIFIED | test_disk_full_style_io_failure_fails_closed |
| GAP15-MC-38-03 | BLOCKED | network/TLS fault injection between real dependencies needs version-pinned GAP-02/GAP-07/GAP-08/SCH-01/PLN-04 environments and execution tiers |
| GAP15-MC-38-04 | BLOCKED | a replicated store (multi-node) — ADR-001 records single-node SQLite only |
| GAP15-MC-38-05 | LOCALLY_VERIFIED | test_dependency_outage_and_retry_after_crash, test_untrusted_time_blocks_decisions |
| GAP15-MC-38-06 | LOCALLY_VERIFIED | test_backup_manifest_and_restore_to_staging, test_restore_refuses_corrupt_forged_and_existing_target |
| GAP15-MC-38-07 | BLOCKED | site loss simulation needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-38-08 | LOCALLY_VERIFIED | test_measured_rpo_rto |
| GAP15-MC-38-09 | LOCALLY_VERIFIED | test_graceful_shutdown_drains_and_readiness_flips, test_process_kill_mid_transaction_recovers |
| GAP15-MC-38-10 | BLOCKED | an authorised release identity to sign GO decisions |
| GAP15-MC-38-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-38-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-38-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-38-14 | PARTIAL | no test tagged to the component's adversarial/negative item 38-10 |
| GAP15-MC-38-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-38-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-38-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-38-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-38-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-38-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-39-01 | LOCALLY_VERIFIED | test_latency_throughput_envelope_recorded |
| GAP15-MC-39-02 | LOCALLY_VERIFIED | test_latency_throughput_envelope_recorded |
| GAP15-MC-39-03 | LOCALLY_VERIFIED | test_latency_throughput_envelope_recorded |
| GAP15-MC-39-04 | LOCALLY_VERIFIED | test_latency_throughput_envelope_recorded |
| GAP15-MC-39-05 | LOCALLY_VERIFIED | test_cardinality_bound_and_benchmark, test_latency_throughput_envelope_recorded |
| GAP15-MC-39-06 | BLOCKED | a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-39-07 | BLOCKED | multi-hour/day soak needs a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-39-08 | BLOCKED | regression budgets on controlled hardware need a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-39-09 | LOCALLY_VERIFIED | test_latency_throughput_envelope_recorded |
| GAP15-MC-39-10 | LOCALLY_VERIFIED | test_latency_throughput_envelope_recorded |
| GAP15-MC-39-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-39-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-39-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-39-14 | LOCALLY_VERIFIED | test_cardinality_bound_and_benchmark, test_latency_throughput_envelope_recorded |
| GAP15-MC-39-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-39-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-39-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-39-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-39-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-39-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-40-01 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-40-02 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-40-03 | BLOCKED | a vulnerability/licence scanner and its database |
| GAP15-MC-40-04 | PARTIAL | migration/restore tests exist; not yet packaged into a signed bundle by a release identity |
| GAP15-MC-40-05 | BLOCKED | signed performance evidence needs an authorised release identity to sign GO decisions |
| GAP15-MC-40-06 | BLOCKED | canary plan/DR proof in the bundle need a scheduled game day / drill with real operators |
| GAP15-MC-40-07 | LOCALLY_VERIFIED | test_gate_explain_lists_every_input |
| GAP15-MC-40-08 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-40-09 | BLOCKED | immutable preservation needs an authorised release identity to sign GO decisions |
| GAP15-MC-40-10 | LOCALLY_VERIFIED | test_gate_rejects_missing_stale_mismatched_unsigned_selfreview |
| GAP15-MC-40-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-40-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-40-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-40-14 | LOCALLY_VERIFIED | test_gate_explain_lists_every_input, test_gate_go_only_with_complete_signed_bound_evidence, test_gate_rejects_missing_stale_mismatched_unsigned_selfreview |
| GAP15-MC-40-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-40-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-40-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-40-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-40-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-40-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-41-01 | LOCALLY_VERIFIED | test_rtm_has_100_rows_linked_to_components_modules_tests |
| GAP15-MC-41-02 | LOCALLY_VERIFIED | test_rtm_has_100_rows_linked_to_components_modules_tests |
| GAP15-MC-41-03 | LOCALLY_VERIFIED | test_rtm_has_100_rows_linked_to_components_modules_tests |
| GAP15-MC-41-04 | PARTIAL | RTM links this build's test results; release-candidate evidence needs an authorised release identity to sign GO decisions |
| GAP15-MC-41-05 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-41-06 | LOCALLY_VERIFIED | test_rtm_problem_detection |
| GAP15-MC-41-07 | LOCALLY_VERIFIED | test_rtm_problem_detection |
| GAP15-MC-41-08 | LOCALLY_VERIFIED | test_rtm_has_100_rows_linked_to_components_modules_tests |
| GAP15-MC-41-09 | LOCALLY_VERIFIED | test_rtm_has_100_rows_linked_to_components_modules_tests |
| GAP15-MC-41-10 | LOCALLY_VERIFIED | test_gate_consumes_rtm_status |
| GAP15-MC-41-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-41-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-41-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-41-14 | LOCALLY_VERIFIED | test_gate_consumes_rtm_status, test_rtm_has_100_rows_linked_to_components_modules_tests, test_rtm_problem_detection |
| GAP15-MC-41-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-41-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-41-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-41-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-41-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-41-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-42-01 | ARTIFACT_PRESENT_UNREVIEWED | test_adr_structure_and_links |
| GAP15-MC-42-02 | ARTIFACT_PRESENT_UNREVIEWED | test_adr_structure_and_links |
| GAP15-MC-42-03 | ARTIFACT_PRESENT_UNREVIEWED | test_adr_structure_and_links |
| GAP15-MC-42-04 | ARTIFACT_PRESENT_UNREVIEWED | test_adr_structure_and_links |
| GAP15-MC-42-05 | ARTIFACT_PRESENT_UNREVIEWED | test_adr_structure_and_links |
| GAP15-MC-42-06 | ARTIFACT_PRESENT_UNREVIEWED | test_retention_privacy_documented |
| GAP15-MC-42-07 | BLOCKED | ADR owners/approvers: named owners, on-call rotation and approvers |
| GAP15-MC-42-08 | ARTIFACT_PRESENT_UNREVIEWED | test_adr_structure_and_links |
| GAP15-MC-42-09 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-42-10 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-42-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-42-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-42-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-42-14 | NOT_IMPLEMENTED |  |
| GAP15-MC-42-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-42-16 | PARTIAL | unresolved rows: GAP15-MC-42-14 |
| GAP15-MC-42-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-42-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-42-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-42-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-43-01 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-02 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-03 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-04 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-05 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-06 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-07 | LOCALLY_VERIFIED | test_owner_validation_reports_placeholders |
| GAP15-MC-43-08 | BLOCKED | named owners, on-call rotation and approvers |
| GAP15-MC-43-09 | LOCALLY_VERIFIED | test_owner_validation_reports_placeholders |
| GAP15-MC-43-10 | BLOCKED | a scheduled game day / drill with real operators |
| GAP15-MC-43-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-43-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-43-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-43-14 | NOT_IMPLEMENTED |  |
| GAP15-MC-43-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-43-16 | PARTIAL | unresolved rows: GAP15-MC-43-14 |
| GAP15-MC-43-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-43-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-43-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-43-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-44-01 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest |
| GAP15-MC-44-02 | ARTIFACT_PRESENT_UNREVIEWED | test_deployment_manifests_least_privilege |
| GAP15-MC-44-03 | LOCALLY_VERIFIED | test_config_schema_secure_defaults_and_secrets |
| GAP15-MC-44-04 | LOCALLY_VERIFIED | test_preflight_and_production_start_refusal |
| GAP15-MC-44-05 | LOCALLY_VERIFIED | test_development_key_provider_refuses_production, test_config_schema_secure_defaults_and_secrets |
| GAP15-MC-44-06 | LOCALLY_VERIFIED | test_config_schema_secure_defaults_and_secrets |
| GAP15-MC-44-07 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest |
| GAP15-MC-44-08 | LOCALLY_VERIFIED | test_preflight_and_production_start_refusal |
| GAP15-MC-44-09 | LOCALLY_VERIFIED | test_forward_only_migration_and_downgrade_refusal |
| GAP15-MC-44-10 | PARTIAL | Linux paths tested; Windows and container runs not executed here |
| GAP15-MC-44-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-44-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-44-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-44-14 | LOCALLY_VERIFIED | test_forward_only_migration_and_downgrade_refusal, test_development_key_provider_refuses_production, test_config_schema_secure_defaults_and_secrets, test_preflight_and_production_start_refusal |
| GAP15-MC-44-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-44-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-44-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-44-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-44-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-44-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-45-01 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest |
| GAP15-MC-45-02 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest |
| GAP15-MC-45-03 | LOCALLY_VERIFIED | test_signed_provenance_verifies_and_tamper_detected |
| GAP15-MC-45-04 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest |
| GAP15-MC-45-05 | BLOCKED | a vulnerability/licence scanner and its database |
| GAP15-MC-45-06 | BLOCKED | patch SLA and support window need named owners, on-call rotation and approvers |
| GAP15-MC-45-07 | BLOCKED | a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-45-08 | PARTIAL | stdlib-only: no dependencies are downloaded; build network isolation not enforced here |
| GAP15-MC-45-09 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest |
| GAP15-MC-45-10 | LOCALLY_VERIFIED | test_signed_provenance_verifies_and_tamper_detected |
| GAP15-MC-45-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-45-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-45-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-45-14 | LOCALLY_VERIFIED | test_sbom_provenance_and_manifest, test_signed_provenance_verifies_and_tamper_detected |
| GAP15-MC-45-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-45-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-45-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-45-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-45-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-45-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-46-01 | LOCALLY_VERIFIED | test_staged_promotion_and_auto_rollback |
| GAP15-MC-46-02 | LOCALLY_VERIFIED | test_staged_promotion_and_auto_rollback |
| GAP15-MC-46-03 | LOCALLY_VERIFIED | test_staged_promotion_and_auto_rollback |
| GAP15-MC-46-04 | LOCALLY_VERIFIED | test_emergency_disable_admissions |
| GAP15-MC-46-05 | LOCALLY_VERIFIED | test_emergency_disable_admissions |
| GAP15-MC-46-06 | LOCALLY_VERIFIED | test_rollback_schema_compat_and_canary_isolation |
| GAP15-MC-46-07 | LOCALLY_VERIFIED | test_revocation_audit_and_restore_preserves_it |
| GAP15-MC-46-08 | LOCALLY_VERIFIED | test_rollback_schema_compat_and_canary_isolation |
| GAP15-MC-46-09 | BLOCKED | a scheduled game day / drill with real operators |
| GAP15-MC-46-10 | BLOCKED | an authorised release identity to sign GO decisions |
| GAP15-MC-46-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-46-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-46-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-46-14 | PARTIAL | no test tagged to the component's adversarial/negative item 46-10 |
| GAP15-MC-46-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-46-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-46-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-46-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-46-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-46-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-47-01 | LOCALLY_VERIFIED | test_backup_manifest_and_restore_to_staging, test_cli_verify_and_export |
| GAP15-MC-47-02 | LOCALLY_VERIFIED | test_backup_manifest_and_restore_to_staging |
| GAP15-MC-47-03 | BLOCKED | an HSM/KMS/TPM key provider (none available to this build) |
| GAP15-MC-47-04 | LOCALLY_VERIFIED | test_backup_manifest_and_restore_to_staging, test_restore_refuses_corrupt_forged_and_existing_target |
| GAP15-MC-47-05 | LOCALLY_VERIFIED | test_forward_only_migration_and_downgrade_refusal |
| GAP15-MC-47-06 | LOCALLY_VERIFIED | test_forward_only_migration_and_downgrade_refusal, test_interrupted_migration_rolls_back |
| GAP15-MC-47-07 | LOCALLY_VERIFIED | test_backup_manifest_and_restore_to_staging, test_deterministic_historical_reconstruction |
| GAP15-MC-47-08 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-47-09 | PARTIAL | backup.run/restore.run actions exist in the authz model; the backup API is CLI/library only, not behind the service authz path |
| GAP15-MC-47-10 | BLOCKED | periodic automated restore verification needs a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-47-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-47-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-47-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-47-14 | PARTIAL | no test tagged to the component's adversarial/negative item 47-10 |
| GAP15-MC-47-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-47-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-47-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-47-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-47-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-47-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-48-01 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-02 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-03 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-04 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-05 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-06 | LOCALLY_VERIFIED | test_cli_verify_and_export, test_runbooks_cover_required_sections |
| GAP15-MC-48-07 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-08 | ARTIFACT_PRESENT_UNREVIEWED | test_runbooks_cover_required_sections |
| GAP15-MC-48-09 | BLOCKED | a scheduled game day / drill with real operators |
| GAP15-MC-48-10 | ARTIFACT_PRESENT_UNREVIEWED | test_runbook_links_resolve |
| GAP15-MC-48-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-48-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-48-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-48-14 | NOT_IMPLEMENTED |  |
| GAP15-MC-48-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-48-16 | PARTIAL | unresolved rows: GAP15-MC-48-14 |
| GAP15-MC-48-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-48-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-48-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-48-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-49-01 | LOCALLY_VERIFIED | test_reactivation_needs_waiver_and_two_people |
| GAP15-MC-49-02 | LOCALLY_VERIFIED | test_reactivation_needs_waiver_and_two_people |
| GAP15-MC-49-03 | LOCALLY_VERIFIED | test_waivers_scoped_non_waivable |
| GAP15-MC-49-04 | LOCALLY_VERIFIED | test_sod_expiry_renewal_history |
| GAP15-MC-49-05 | LOCALLY_VERIFIED | test_sod_expiry_renewal_history |
| GAP15-MC-49-06 | LOCALLY_VERIFIED | test_sod_expiry_renewal_history |
| GAP15-MC-49-07 | LOCALLY_VERIFIED | test_waivers_scoped_non_waivable |
| GAP15-MC-49-08 | LOCALLY_VERIFIED | test_sod_expiry_renewal_history |
| GAP15-MC-49-09 | LOCALLY_VERIFIED | test_governance_report |
| GAP15-MC-49-10 | LOCALLY_VERIFIED | test_sod_expiry_renewal_history |
| GAP15-MC-49-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-49-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-49-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-49-14 | LOCALLY_VERIFIED | test_reactivation_needs_waiver_and_two_people, test_waivers_scoped_non_waivable, test_governance_report, test_sod_expiry_renewal_history |
| GAP15-MC-49-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-49-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-49-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-49-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-49-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-49-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-50-01 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-50-02 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-50-03 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence, test_gate_rejects_missing_stale_mismatched_unsigned_selfreview |
| GAP15-MC-50-04 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-50-05 | LOCALLY_VERIFIED | test_gate_go_only_with_complete_signed_bound_evidence |
| GAP15-MC-50-06 | BLOCKED | an authorised release identity to sign GO decisions |
| GAP15-MC-50-07 | BLOCKED | deployment automation integration needs a CI system with protected branches, ephemeral runners and scheduled jobs |
| GAP15-MC-50-08 | NOT_IMPLEMENTED | no separate emergency-override path exists in the exit gate (by design it only says NO_GO) |
| GAP15-MC-50-09 | LOCALLY_VERIFIED | test_gate_explain_lists_every_input |
| GAP15-MC-50-10 | LOCALLY_VERIFIED | test_gate_rejects_missing_stale_mismatched_unsigned_selfreview |
| GAP15-MC-50-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-50-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-50-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-50-14 | LOCALLY_VERIFIED | test_gate_explain_lists_every_input, test_gate_go_only_with_complete_signed_bound_evidence, test_gate_rejects_missing_stale_mismatched_unsigned_selfreview, test_release_key_cannot_sign_review |
| GAP15-MC-50-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-50-16 | PARTIAL | unresolved rows: GAP15-MC-50-08 |
| GAP15-MC-50-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-50-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-50-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-50-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-MC-51-01 | BLOCKED | the authoritative original MASTER.md from the v4.1.0 source lineage |
| GAP15-MC-51-02 | BLOCKED | the authoritative original MASTER.md from the v4.1.0 source lineage |
| GAP15-MC-51-03 | BLOCKED | the authoritative original MASTER.md from the v4.1.0 source lineage |
| GAP15-MC-51-04 | BLOCKED | the authoritative original MASTER.md from the v4.1.0 source lineage |
| GAP15-MC-51-05 | BLOCKED | the authoritative original MASTER.md from the v4.1.0 source lineage |
| GAP15-MC-51-06 | BLOCKED | the authoritative original MASTER.md from the v4.1.0 source lineage |
| GAP15-MC-51-07 | LOCALLY_VERIFIED | test_master_md_absence_is_reported_not_invented |
| GAP15-MC-51-08 | LOCALLY_VERIFIED | test_master_md_absence_is_reported_not_invented |
| GAP15-MC-51-09 | LOCALLY_VERIFIED | test_master_md_absence_is_reported_not_invented |
| GAP15-MC-51-10 | LOCALLY_VERIFIED | test_master_md_absence_is_reported_not_invented |
| GAP15-MC-51-11 | NOT_APPLICABLE | no runtime configuration: this component is a verification/release/governance artifact, not a running subsystem |
| GAP15-MC-51-12 | NOT_APPLICABLE | no runtime telemetry: this component is a verification/release/governance artifact; its outputs are machine-readable evidence files rather than a running subsystem |
| GAP15-MC-51-13 | ARTIFACT_PRESENT_UNREVIEWED | test_one_threat_row_per_component |
| GAP15-MC-51-14 | LOCALLY_VERIFIED | test_master_md_absence_is_reported_not_invented |
| GAP15-MC-51-15 | ARTIFACT_PRESENT_UNREVIEWED | test_every_component_mapped_to_runbook |
| GAP15-MC-51-16 | LOCALLY_VERIFIED | py (RTM generation) |
| GAP15-MC-51-17 | BLOCKED | an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-MC-51-EXIT-01 | BLOCKED | proof of no bypass in a deployed production path needs a fleet/lab estate, real hardware profiles and a production-like deployment |
| GAP15-MC-51-EXIT-02 | BLOCKED | release-candidate evidence tied to a build digest and signed needs an authorised release identity to sign GO decisions |
| GAP15-MC-51-EXIT-03 | BLOCKED | ownership, game-day-tested runbooks and release-gate evidence need named owners, on-call rotation and approvers |
| GAP15-SIGNOFF-001 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-002 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-003 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-004 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-005 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-006 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-007 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-008 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-009 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
| GAP15-SIGNOFF-010 | BLOCKED | release-level gate over all components; open blockers remain (see BLOCKED rows) and an independent human reviewer and a signed review record; the builder cannot review its own work, and no owner is assigned in docs/OWNERS.json |
