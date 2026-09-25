# GAP-11 traceability matrix (generated)

| Check | Status | Evidence |
|---|---|---|
| GAP11-P0-01.01 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_state_machines_reject_illegal_transitions |
| GAP11-P0-01.02 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_multi_key_cas_is_all_or_nothing |
| GAP11-P0-01.03 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_multi_key_cas_is_all_or_nothing |
| GAP11-P0-01.04 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_crash_at_every_write_point |
| GAP11-P0-01.05 | EVIDENCED | 2 passing test(s); test_state.StoreTests.test_crash_at_every_write_point, test_state.StoreTests.test_restart_cannot_manufacture_or_lose_ownership |
| GAP11-P0-01.06 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_wall_clock_skew_does_not_affect_correctness |
| GAP11-P0-01.07 | EVIDENCED | 2 passing test(s); test_state.TTLAndReconcileTests.test_heartbeat_revives_suspect_and_crash_mid_scrub_quarantines, test_state.TTLAndReconcileTests.test_reconcile_is_destructive_only_on_unambiguous_evidence |
| GAP11-P0-01.08 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_deposed_leader_cannot_allocate_release_scrub_or_unquarantine |
| GAP11-P0-01.09 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_mutation_provenance_recorded |
| GAP11-P0-01.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK-; test_state.StoreTests.test_disk_full_rolls_back_partial_append_and_corruption_fails_closed, test_state.StoreTests.test_snapshot_compaction_roundtrip_and_read_only_mode |
| GAP11-P0-01.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-01 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-01.12 | EVIDENCED | docs/REQUIREMENTS.json: 8 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-01-Rnn |
| GAP11-P0-01.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-01.14 | EVIDENCED | invariants INV-STORE-1, INV-STORE-2, INV-STORE-3 enforced in code and asserted by tagged tests |
| GAP11-P0-01.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-01.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-01.17 | EVIDENCED | reason codes STORE_CORRUPT, STORE_UNAVAILABLE, STALE_REVISION registered and emitted |
| GAP11-P0-01.18 | EVIDENCED | 9 tagged tests assert refusals/fault paths |
| GAP11-P0-01.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-01.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-02.01 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_state_machines_reject_illegal_transitions |
| GAP11-P0-02.02 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_multi_key_cas_is_all_or_nothing |
| GAP11-P0-02.03 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_deposed_leader_cannot_allocate_release_scrub_or_unquarantine |
| GAP11-P0-02.04 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_crash_at_every_write_point |
| GAP11-P0-02.05 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_crash_at_every_write_point |
| GAP11-P0-02.06 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_wall_clock_skew_does_not_affect_correctness |
| GAP11-P0-02.07 | OPEN | no test or artifact evidences this item |
| GAP11-P0-02.08 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_deposed_leader_cannot_allocate_release_scrub_or_unquarantine |
| GAP11-P0-02.09 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_leadership_changes_have_provenance_and_telemetry |
| GAP11-P0-02.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK- |
| GAP11-P0-02.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-02 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-02.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-02-Rnn |
| GAP11-P0-02.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-02.14 | EVIDENCED | invariants INV-FENCE-1, INV-FENCE-2 enforced in code and asserted by tagged tests |
| GAP11-P0-02.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-02.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-02.17 | EVIDENCED | reason codes STALE_FENCE registered and emitted |
| GAP11-P0-02.18 | EVIDENCED | 5 tagged tests assert refusals/fault paths |
| GAP11-P0-02.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-02.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-03.01 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_single_leader_and_epoch_monotonic_across_failovers |
| GAP11-P0-03.02 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_single_leader_and_epoch_monotonic_across_failovers |
| GAP11-P0-03.03 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_deposed_leader_cannot_allocate_release_scrub_or_unquarantine |
| GAP11-P0-03.04 | EVIDENCED | 1 passing test(s); test_state.CrossComponentRecoveryTests.test_crash_during_leader_acquisition |
| GAP11-P0-03.05 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_single_leader_and_epoch_monotonic_across_failovers |
| GAP11-P0-03.06 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_wall_clock_skew_does_not_affect_correctness |
| GAP11-P0-03.07 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_step_down_hands_over_without_waiting_for_ttl |
| GAP11-P0-03.08 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_deposed_leader_cannot_allocate_release_scrub_or_unquarantine |
| GAP11-P0-03.09 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_leadership_changes_have_provenance_and_telemetry |
| GAP11-P0-03.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK- |
| GAP11-P0-03.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-03 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-03.12 | EVIDENCED | docs/REQUIREMENTS.json: 6 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-03-Rnn |
| GAP11-P0-03.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-03.14 | EVIDENCED | invariants INV-LEAD-1, INV-LEAD-2 enforced in code and asserted by tagged tests |
| GAP11-P0-03.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-03.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-03.17 | EVIDENCED | reason codes NOT_LEADER, leader_change registered and emitted |
| GAP11-P0-03.18 | EVIDENCED | 4 tagged tests assert refusals/fault paths |
| GAP11-P0-03.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-03.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-04.01 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_state_machines_reject_illegal_transitions |
| GAP11-P0-04.02 | EVIDENCED | 1 passing test(s); test_state.TTLAndReconcileTests.test_reconcile_is_destructive_only_on_unambiguous_evidence |
| GAP11-P0-04.03 | EVIDENCED | 1 passing test(s); test_state.TTLAndReconcileTests.test_reconcile_is_destructive_only_on_unambiguous_evidence |
| GAP11-P0-04.04 | EVIDENCED | 1 passing test(s); test_state.TTLAndReconcileTests.test_heartbeat_revives_suspect_and_crash_mid_scrub_quarantines |
| GAP11-P0-04.05 | EVIDENCED | 1 passing test(s); test_state.TTLAndReconcileTests.test_heartbeat_revives_suspect_and_crash_mid_scrub_quarantines |
| GAP11-P0-04.06 | EVIDENCED | 1 passing test(s); test_state.FencingElectionTests.test_wall_clock_skew_does_not_affect_correctness |
| GAP11-P0-04.07 | EVIDENCED | 1 passing test(s); test_state.TTLAndReconcileTests.test_reconcile_is_destructive_only_on_unambiguous_evidence |
| GAP11-P0-04.08 | EVIDENCED | 1 passing test(s); test_state.CrossComponentRecoveryTests.test_deposed_leader_cannot_reclaim_and_reclaims_carry_provenance |
| GAP11-P0-04.09 | EVIDENCED | 1 passing test(s); test_state.CrossComponentRecoveryTests.test_deposed_leader_cannot_reclaim_and_reclaims_carry_provenance |
| GAP11-P0-04.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK- |
| GAP11-P0-04.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-04 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-04.12 | EVIDENCED | docs/REQUIREMENTS.json: 5 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-04-Rnn |
| GAP11-P0-04.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-04.14 | EVIDENCED | invariants INV-TTL-1, INV-TTL-2 enforced in code and asserted by tagged tests |
| GAP11-P0-04.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-04.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-04.17 | EVIDENCED | reason codes AMBIGUOUS_EVIDENCE, LEASE_EXPIRED registered and emitted |
| GAP11-P0-04.18 | EVIDENCED | 4 tagged tests assert refusals/fault paths |
| GAP11-P0-04.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-04.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-05.01 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_replay_returns_original_result_and_conflict_is_refused |
| GAP11-P0-05.02 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_replay_returns_original_result_and_conflict_is_refused |
| GAP11-P0-05.03 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_replay_returns_original_result_and_conflict_is_refused |
| GAP11-P0-05.04 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_ack_lost_after_commit_then_retry_after_restart |
| GAP11-P0-05.05 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_ack_lost_after_commit_then_retry_after_restart |
| GAP11-P0-05.06 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_idempotency_retention_window |
| GAP11-P0-05.07 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_replay_returns_original_result_and_conflict_is_refused |
| GAP11-P0-05.08 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_request_ids_are_tenant_scoped_at_the_boundary_and_recorded |
| GAP11-P0-05.09 | EVIDENCED | 1 passing test(s); test_state.IdempotencyTests.test_request_ids_are_tenant_scoped_at_the_boundary_and_recorded |
| GAP11-P0-05.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK- |
| GAP11-P0-05.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-05 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-05.12 | EVIDENCED | docs/REQUIREMENTS.json: 5 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-05-Rnn |
| GAP11-P0-05.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-05.14 | EVIDENCED | invariants INV-IDEM-1, INV-IDEM-2 enforced in code and asserted by tagged tests |
| GAP11-P0-05.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-05.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-05.17 | EVIDENCED | reason codes IDEMPOTENCY_CONFLICT, DUPLICATE_REQUEST registered and emitted |
| GAP11-P0-05.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P0-05.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-05.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-06.01 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.InventoryTests.test_vendor_payloads_normalise_to_one_canonical_model |
| GAP11-P0-06.02 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.InventoryTests.test_vendor_payloads_normalise_to_one_canonical_model |
| GAP11-P0-06.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.InventoryTests.test_stable_identity_survives_pci_renumbering_and_replacement_is_distinguished |
| GAP11-P0-06.04 | BLOCKED | capability validation against LIVE hardware: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment |
| GAP11-P0-06.05 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.InventoryTests.test_stable_identity_survives_pci_renumbering_and_replacement_is_distinguished |
| GAP11-P0-06.06 | PARTIAL | bounded deadlines, exponential backoff and non-retryable classes implemented (hardware.with_retry, ScrubExecutor); no cancellation token | local evidence: 1 tes; test_hardware.InventoryTests.test_bounded_retry_and_failed_provider_is_unknown_not_removed |
| GAP11-P0-06.07 | BLOCKED | privileged node-agent process separation not built (no hardware/OS agent to separate): BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/F |
| GAP11-P0-06.08 | PARTIAL | independent post-operation verification implemented and tested against simulators only: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/ |
| GAP11-P0-06.09 | PARTIAL | structured evidence records (PK_INVENTORY_EVIDENCE/1, PK_SCRUB_EVIDENCE/1) carry identity, steps, timing, result; controller/request lineage is joined only via ; test_hardware.InventoryTests.test_inventory_evidence_is_structured |
| GAP11-P0-06.10 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.InventoryTests.test_bounded_retry_and_failed_provider_is_unknown_not_removed |
| GAP11-P0-06.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-06 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-06.12 | EVIDENCED | docs/REQUIREMENTS.json: 6 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-06-Rnn |
| GAP11-P0-06.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-06.14 | EVIDENCED | invariants INV-INV-1, INV-INV-2 enforced in code and asserted by tagged tests |
| GAP11-P0-06.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-06.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-06.17 | EVIDENCED | reason codes DEADLINE_EXCEEDED, SCHEMA_INVALID registered and emitted |
| GAP11-P0-06.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P0-06.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-06.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-07.01 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.PartitionTopologyTests.test_alternative_layouts_are_mutually_exclusive_and_reconfigure_only_when_drained |
| GAP11-P0-07.02 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.PartitionTopologyTests.test_alternative_layouts_are_mutually_exclusive_and_reconfigure_only_when_drained |
| GAP11-P0-07.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.PartitionTopologyTests.test_partition_names_survive_reconfigure_round_trip |
| GAP11-P0-07.04 | BLOCKED | capability validation against LIVE hardware: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment |
| GAP11-P0-07.05 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.PartitionTopologyTests.test_alternative_layouts_are_mutually_exclusive_and_reconfigure_only_when_drained |
| GAP11-P0-07.06 | PARTIAL | bounded deadlines, exponential backoff and non-retryable classes implemented (hardware.with_retry, ScrubExecutor); no cancellation token | reconfigure() has no  |
| GAP11-P0-07.07 | BLOCKED | privileged node-agent process separation not built (no hardware/OS agent to separate): BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/F |
| GAP11-P0-07.08 | PARTIAL | independent post-operation verification implemented and tested against simulators only: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/ |
| GAP11-P0-07.09 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P0-07.10 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.PartitionTopologyTests.test_profile_choice_minimises_residual_capacity |
| GAP11-P0-07.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-07 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-07.12 | EVIDENCED | docs/REQUIREMENTS.json: 6 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-07-Rnn |
| GAP11-P0-07.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-07.14 | EVIDENCED | invariants INV-PART-1, INV-PART-2 enforced in code and asserted by tagged tests |
| GAP11-P0-07.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-07.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-07.17 | EVIDENCED | reason codes ILLEGAL_TRANSITION, CONFIG_INVALID registered and emitted |
| GAP11-P0-07.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P0-07.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-07.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-08.01 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ScrubTests.test_scrub_success_writes_evidence |
| GAP11-P0-08.02 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ScrubTests.test_partial_zeroize_timeout_and_permanent_fault_all_quarantine |
| GAP11-P0-08.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ScrubTests.test_controller_quarantines_on_failed_scrub_and_blocks_cross_tenant_reuse |
| GAP11-P0-08.04 | BLOCKED | capability validation against LIVE hardware: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment | local ; test_hardware.ScrubTests.test_no_scrub_executor_fails_closed |
| GAP11-P0-08.05 | EVIDENCED | 2 passing test(s) against simulated providers; test_hardware.ScrubTests.test_controller_quarantines_on_failed_scrub_and_blocks_cross_tenant_reuse, test_state.TTLAndReconcileTests.test_heartbeat_revives_suspect_and_crash_mid_scrub_quarantines |
| GAP11-P0-08.06 | PARTIAL | bounded deadlines, exponential backoff and non-retryable classes implemented (hardware.with_retry, ScrubExecutor); no cancellation token | local evidence: 1 tes; test_hardware.ScrubTests.test_partial_zeroize_timeout_and_permanent_fault_all_quarantine |
| GAP11-P0-08.07 | BLOCKED | privileged node-agent process separation not built (no hardware/OS agent to separate): BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/F |
| GAP11-P0-08.08 | PARTIAL | independent post-operation verification implemented and tested against simulators only: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/ |
| GAP11-P0-08.09 | PARTIAL | structured evidence records (PK_INVENTORY_EVIDENCE/1, PK_SCRUB_EVIDENCE/1) carry identity, steps, timing, result; controller/request lineage is joined only via ; test_hardware.ScrubTests.test_scrub_success_writes_evidence |
| GAP11-P0-08.10 | EVIDENCED | 2 passing test(s) against simulated providers; test_hardware.ScrubTests.test_partial_zeroize_timeout_and_permanent_fault_all_quarantine, test_hardware.ScrubTests.test_scrub_success_writes_evidence |
| GAP11-P0-08.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-08 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-08.12 | EVIDENCED | docs/REQUIREMENTS.json: 6 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-08-Rnn |
| GAP11-P0-08.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-08.14 | EVIDENCED | invariants INV-SCRUB-1, INV-SCRUB-2 enforced in code and asserted by tagged tests |
| GAP11-P0-08.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-08.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-08.17 | EVIDENCED | reason codes SCRUB_FAILED, SCRUB_TIMEOUT registered and emitted |
| GAP11-P0-08.18 | EVIDENCED | 4 tagged tests assert refusals/fault paths |
| GAP11-P0-08.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-08.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-09.01 | EVIDENCED | docs/THREAT_MODEL.md trust-boundary table TB-1..TB-6; test_security.AttestationTests.test_quote_binds_node_device_capability_and_firmware |
| GAP11-P0-09.02 | PARTIAL | HMAC workload-identity credentials verified on every state change; mutually authenticated channel (mTLS) absent: BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 a; test_security.AttestationTests.test_quote_binds_node_device_capability_and_firmware |
| GAP11-P0-09.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AttestationTests.test_quote_binds_node_device_capability_and_firmware |
| GAP11-P0-09.04 | OPEN | no test or artifact evidences this item (component blockers: BLK-PKI; BLK-ADJ) |
| GAP11-P0-09.05 | OPEN | no test or artifact evidences this item (component blockers: BLK-PKI; BLK-ADJ) |
| GAP11-P0-09.06 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AttestationTests.test_quote_binds_node_device_capability_and_firmware |
| GAP11-P0-09.07 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AttestationTests.test_firmware_allowlist_and_verifier_key_rotation |
| GAP11-P0-09.08 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthzTests.test_sensitive_inventory_and_redaction |
| GAP11-P0-09.09 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AttestationTests.test_firmware_allowlist_and_verifier_key_rotation |
| GAP11-P0-09.10 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AttestationTests.test_quote_binds_node_device_capability_and_firmware |
| GAP11-P0-09.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-09 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-09.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-09-Rnn |
| GAP11-P0-09.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-09.14 | EVIDENCED | invariants INV-ATT-1 enforced in code and asserted by tagged tests |
| GAP11-P0-09.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-09.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-09.17 | EVIDENCED | reason codes ATTESTATION_INVALID registered and emitted |
| GAP11-P0-09.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P0-09.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-09.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-10.01 | EVIDENCED | docs/THREAT_MODEL.md trust-boundary table TB-1..TB-6 |
| GAP11-P0-10.02 | PARTIAL | HMAC workload-identity credentials verified on every state change; mutually authenticated channel (mTLS) absent: BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 a; test_security.AuthnTests.test_forged_expired_replayed_and_wrong_audience_credentials_refused |
| GAP11-P0-10.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthnTests.test_forged_expired_replayed_and_wrong_audience_credentials_refused |
| GAP11-P0-10.04 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthzTests.test_deny_by_default_scopes_operator_only_and_cross_tenant |
| GAP11-P0-10.05 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthzTests.test_deny_by_default_scopes_operator_only_and_cross_tenant |
| GAP11-P0-10.06 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthnTests.test_forged_expired_replayed_and_wrong_audience_credentials_refused |
| GAP11-P0-10.07 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthnTests.test_live_key_rotation_with_overlap_and_emergency_revocation |
| GAP11-P0-10.08 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthzTests.test_sensitive_inventory_and_redaction |
| GAP11-P0-10.09 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthnTests.test_identity_policy_and_kms_outages_fail_closed |
| GAP11-P0-10.10 | EVIDENCED | 2 passing test(s) against simulated providers; test_security.AuthnTests.test_forged_expired_replayed_and_wrong_audience_credentials_refused, test_security.AuthzTests.test_confused_deputy_and_cross_tenant_release_through_the_service |
| GAP11-P0-10.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-10 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-10.12 | EVIDENCED | docs/REQUIREMENTS.json: 5 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-10-Rnn |
| GAP11-P0-10.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-10.14 | EVIDENCED | invariants INV-AUTHN-1 enforced in code and asserted by tagged tests |
| GAP11-P0-10.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-10.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-10.17 | EVIDENCED | reason codes UNAUTHENTICATED, REPLAY_DETECTED registered and emitted |
| GAP11-P0-10.18 | EVIDENCED | 5 tagged tests assert refusals/fault paths |
| GAP11-P0-10.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-10.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-11.01 | EVIDENCED | docs/THREAT_MODEL.md trust-boundary table TB-1..TB-6 |
| GAP11-P0-11.02 | PARTIAL | HMAC workload-identity credentials verified on every state change; mutually authenticated channel (mTLS) absent: BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 a; test_security.AuthzTests.test_confused_deputy_and_cross_tenant_release_through_the_service |
| GAP11-P0-11.03 | EVIDENCED | 1 passing test(s); test_security.AuthnTests.test_forged_expired_replayed_and_wrong_audience_credentials_refused |
| GAP11-P0-11.04 | EVIDENCED | 1 passing test(s); test_security.AuthzTests.test_deny_by_default_scopes_operator_only_and_cross_tenant |
| GAP11-P0-11.05 | EVIDENCED | 1 passing test(s); test_security.AuthzTests.test_deny_by_default_scopes_operator_only_and_cross_tenant |
| GAP11-P0-11.06 | EVIDENCED | 1 passing test(s); test_security.AuthzTests.test_confused_deputy_and_cross_tenant_release_through_the_service |
| GAP11-P0-11.07 | OPEN | no test or artifact evidences this item |
| GAP11-P0-11.08 | EVIDENCED | 1 passing test(s); test_security.AuthzTests.test_sensitive_inventory_and_redaction |
| GAP11-P0-11.09 | EVIDENCED | 1 passing test(s); test_security.AuthnTests.test_identity_policy_and_kms_outages_fail_closed |
| GAP11-P0-11.10 | EVIDENCED | 2 passing test(s); test_security.AuthzTests.test_confused_deputy_and_cross_tenant_release_through_the_service, test_security.AuthzTests.test_deny_by_default_scopes_operator_only_and_cross_tenant |
| GAP11-P0-11.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-11 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-11.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-11-Rnn |
| GAP11-P0-11.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-11.14 | EVIDENCED | invariants INV-AUTHZ-1, INV-AUTHZ-2 enforced in code and asserted by tagged tests |
| GAP11-P0-11.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P0-11.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-11.17 | EVIDENCED | reason codes POLICY_DENIED registered and emitted |
| GAP11-P0-11.18 | EVIDENCED | 4 tagged tests assert refusals/fault paths |
| GAP11-P0-11.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-11.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-12.01 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_every_schema_has_limits_and_every_code_is_registered |
| GAP11-P0-12.02 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_every_schema_has_limits_and_every_code_is_registered |
| GAP11-P0-12.03 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_compatibility_rules_closed_requests_open_responses |
| GAP11-P0-12.04 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_limits_enforced_before_business_logic |
| GAP11-P0-12.05 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_trace_and_request_id_propagate_end_to_end |
| GAP11-P0-12.06 | PARTIAL | bounded in-flight semaphore + bounded fair queue + quotas tested; per-principal rate limiting not implemented | local evidence: 1 test(s); test_wire.TransportTests.test_bounded_inflight_returns_overloaded_not_queueing_forever |
| GAP11-P0-12.07 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_deadline_exceeded_before_state_change |
| GAP11-P0-12.08 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_http_binding_end_to_end_with_retry_idempotency |
| GAP11-P0-12.09 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_golden_fixtures_decode_and_reencode |
| GAP11-P0-12.10 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_decoder_fuzz_never_raises_untyped |
| GAP11-P0-12.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-12 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-12.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-12-Rnn |
| GAP11-P0-12.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-12.14 | EVIDENCED | invariants INV-WIRE-1 enforced in code and asserted by tagged tests |
| GAP11-P0-12.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P0-12.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-12.17 | EVIDENCED | reason codes SCHEMA_INVALID, MESSAGE_TOO_LARGE registered and emitted |
| GAP11-P0-12.18 | EVIDENCED | 7 tagged tests assert refusals/fault paths |
| GAP11-P0-12.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-12.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-13.01 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_every_schema_has_limits_and_every_code_is_registered |
| GAP11-P0-13.02 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_every_schema_has_limits_and_every_code_is_registered |
| GAP11-P0-13.03 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_compatibility_rules_closed_requests_open_responses |
| GAP11-P0-13.04 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_limits_enforced_before_business_logic |
| GAP11-P0-13.05 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_trace_and_request_id_propagate_end_to_end |
| GAP11-P0-13.06 | PARTIAL | bounded in-flight semaphore + bounded fair queue + quotas tested; per-principal rate limiting not implemented | local evidence: 1 test(s); test_wire.TransportTests.test_bounded_inflight_returns_overloaded_not_queueing_forever |
| GAP11-P0-13.07 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_deadline_exceeded_before_state_change |
| GAP11-P0-13.08 | EVIDENCED | 2 passing test(s); test_state.IdempotencyTests.test_replay_returns_original_result_and_conflict_is_refused, test_wire.TransportTests.test_http_binding_end_to_end_with_retry_idempotency |
| GAP11-P0-13.09 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_golden_fixtures_decode_and_reencode |
| GAP11-P0-13.10 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_decoder_fuzz_never_raises_untyped |
| GAP11-P0-13.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-13 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-13.12 | EVIDENCED | docs/REQUIREMENTS.json: 5 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-13-Rnn |
| GAP11-P0-13.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-13.14 | EVIDENCED | invariants INV-SVC-1 enforced in code and asserted by tagged tests |
| GAP11-P0-13.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P0-13.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-13.17 | EVIDENCED | reason codes OVERLOADED, DEADLINE_EXCEEDED registered and emitted |
| GAP11-P0-13.18 | EVIDENCED | 8 tagged tests assert refusals/fault paths |
| GAP11-P0-13.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-13.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-14.01 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_candidates_share_fabric_domain |
| GAP11-P0-14.02 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P0-14.03 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P0-14.04 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_decisions_independent_of_input_order |
| GAP11-P0-14.05 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_allocation_is_all_or_nothing |
| GAP11-P0-14.06 | EVIDENCED | 3 passing test(s); test_scheduler.QuotaFairnessTests.test_fair_queue_starvation_bound_and_backpressure, test_scheduler.QuotaFairnessTests.test_quota_secure_default_and_caps |
| GAP11-P0-14.07 | EVIDENCED | 2 passing test(s); test_hardware.PartitionTopologyTests.test_profile_choice_minimises_residual_capacity, test_scheduler.FragmentationTests.test_fragmentation_metric_and_slice_placement |
| GAP11-P0-14.08 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_victim_eligibility |
| GAP11-P0-14.09 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P0-14.10 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P0-14.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-14 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-14.12 | EVIDENCED | docs/REQUIREMENTS.json: 5 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-14-Rnn |
| GAP11-P0-14.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-14.14 | EVIDENCED | invariants INV-Q-1, INV-Q-2 enforced in code and asserted by tagged tests |
| GAP11-P0-14.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P0-14.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-14.17 | EVIDENCED | reason codes QUOTA_EXCEEDED, OVERLOADED registered and emitted |
| GAP11-P0-14.18 | EVIDENCED | 4 tagged tests assert refusals/fault paths |
| GAP11-P0-14.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-14.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-15.01 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_state_machines_reject_illegal_transitions |
| GAP11-P0-15.02 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_lifecycle_hooks |
| GAP11-P0-15.03 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_lifecycle_hooks |
| GAP11-P0-15.04 | EVIDENCED | 1 passing test(s); test_state.CrossComponentRecoveryTests.test_lifecycle_event_survives_restart_and_is_fenced |
| GAP11-P0-15.05 | EVIDENCED | 1 passing test(s); test_state.CrossComponentRecoveryTests.test_lifecycle_event_survives_restart_and_is_fenced |
| GAP11-P0-15.06 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_hotplug_events_are_monotonic_time_and_recorded |
| GAP11-P0-15.07 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_lifecycle_hooks |
| GAP11-P0-15.08 | EVIDENCED | 1 passing test(s); test_state.CrossComponentRecoveryTests.test_lifecycle_event_survives_restart_and_is_fenced |
| GAP11-P0-15.09 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_lifecycle_hooks |
| GAP11-P0-15.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK- |
| GAP11-P0-15.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-15 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-15.12 | EVIDENCED | docs/REQUIREMENTS.json: 5 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-15-Rnn |
| GAP11-P0-15.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-15.14 | EVIDENCED | invariants INV-LC-1 enforced in code and asserted by tagged tests |
| GAP11-P0-15.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P0-15.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-15.17 | EVIDENCED | reason codes ILLEGAL_TRANSITION, LEASE_NOT_FOUND registered and emitted |
| GAP11-P0-15.18 | EVIDENCED | 3 tagged tests assert refusals/fault paths |
| GAP11-P0-15.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-15.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P0-16.01 | EVIDENCED | 1 passing test(s); test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check |
| GAP11-P0-16.02 | EVIDENCED | 1 passing test(s); test_verification.HermeticityTests.test_control_path_never_reads_wall_clock_or_unseeded_randomness_for_decisions |
| GAP11-P0-16.03 | EVIDENCED | 1 passing test(s); test_verification.FaultMatrixTests.test_fault_matrix |
| GAP11-P0-16.04 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_partitioned_old_leader_with_delayed_messages_cannot_double_allocate |
| GAP11-P0-16.05 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_barrier_collisions_allocate_release_scrub_reconcile_failover |
| GAP11-P0-16.06 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_partitioned_old_leader_with_delayed_messages_cannot_double_allocate |
| GAP11-P0-16.07 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P0-16.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P0-16.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind; test_verification.BenchmarkTests.test_latency_thresholds_local_reference_host |
| GAP11-P0-16.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes |
| GAP11-P0-16.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P0-16 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P0-16.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P0-16-Rnn |
| GAP11-P0-16.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P0-16.14 | EVIDENCED | invariants INV-SB-1 enforced in code and asserted by tagged tests |
| GAP11-P0-16.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P0-16.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P0-16.17 | EVIDENCED | reason codes STALE_FENCE registered and emitted |
| GAP11-P0-16.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P0-16.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P0-16.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-17.01 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_candidates_share_fabric_domain |
| GAP11-P1-17.02 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P1-17.03 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_candidates_share_fabric_domain |
| GAP11-P1-17.04 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_decisions_independent_of_input_order |
| GAP11-P1-17.05 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_allocation_is_all_or_nothing |
| GAP11-P1-17.06 | EVIDENCED | 1 passing test(s); test_scheduler.QuotaFairnessTests.test_fair_queue_starvation_bound_and_backpressure |
| GAP11-P1-17.07 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P1-17.08 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P1-17.09 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P1-17.10 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P1-17.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-17 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-17.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-17-Rnn |
| GAP11-P1-17.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-17.14 | EVIDENCED | invariants INV-GANG-1 enforced in code and asserted by tagged tests |
| GAP11-P1-17.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-17.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-17.17 | EVIDENCED | reason codes CAPACITY_EXHAUSTED registered and emitted |
| GAP11-P1-17.18 | EVIDENCED | 3 tagged tests assert refusals/fault paths |
| GAP11-P1-17.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-17.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-18.01 | EVIDENCED | 1 passing test(s); test_scheduler.FragmentationTests.test_fragmentation_metric_and_slice_placement |
| GAP11-P1-18.02 | EVIDENCED | 1 passing test(s); test_scheduler.FragmentationTests.test_whole_device_lease_blocks_slices_and_vice_versa |
| GAP11-P1-18.03 | EVIDENCED | 1 passing test(s); test_scheduler.FragmentationTests.test_fragmentation_metric_and_slice_placement |
| GAP11-P1-18.04 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_decisions_independent_of_input_order |
| GAP11-P1-18.05 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_allocation_is_all_or_nothing |
| GAP11-P1-18.06 | EVIDENCED | 1 passing test(s); test_scheduler.FragmentationTests.test_whole_device_lease_blocks_slices_and_vice_versa |
| GAP11-P1-18.07 | EVIDENCED | 2 passing test(s); test_hardware.PartitionTopologyTests.test_profile_choice_minimises_residual_capacity, test_scheduler.FragmentationTests.test_fragmentation_metric_and_slice_placement |
| GAP11-P1-18.08 | OPEN | no test or artifact evidences this item |
| GAP11-P1-18.09 | EVIDENCED | 1 passing test(s); test_scheduler.FragmentationTests.test_whole_device_lease_blocks_slices_and_vice_versa |
| GAP11-P1-18.10 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P1-18.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-18 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-18.12 | EVIDENCED | docs/REQUIREMENTS.json: 2 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-18-Rnn |
| GAP11-P1-18.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-18.14 | EVIDENCED | invariants INV-FRAG-1 enforced in code and asserted by tagged tests |
| GAP11-P1-18.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-18.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-18.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-18.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P1-18.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-18.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-19.01 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_thermal_admission_fails_closed_on_stale_or_hot |
| GAP11-P1-19.02 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_thermal_admission_fails_closed_on_stale_or_hot |
| GAP11-P1-19.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_thermally_unavailable_device_cannot_be_leased |
| GAP11-P1-19.04 | BLOCKED | capability validation against LIVE hardware: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment |
| GAP11-P1-19.05 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_thermal_admission_fails_closed_on_stale_or_hot |
| GAP11-P1-19.06 | PARTIAL | bounded deadlines, exponential backoff and non-retryable classes implemented (hardware.with_retry, ScrubExecutor); no cancellation token | local evidence: 1 tes; test_hardware.ThermalHealthTests.test_thermally_unavailable_device_cannot_be_leased |
| GAP11-P1-19.07 | BLOCKED | privileged node-agent process separation not built (no hardware/OS agent to separate): BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/F |
| GAP11-P1-19.08 | PARTIAL | independent post-operation verification implemented and tested against simulators only: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/ |
| GAP11-P1-19.09 | OPEN | no test or artifact evidences this item (component blockers: BLK-ADJ) |
| GAP11-P1-19.10 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_thermal_admission_fails_closed_on_stale_or_hot |
| GAP11-P1-19.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-19 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-19.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-19-Rnn |
| GAP11-P1-19.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-19.14 | EVIDENCED | invariants INV-THERM-1 enforced in code and asserted by tagged tests |
| GAP11-P1-19.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-19.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-19.17 | EVIDENCED | reason codes THERMAL_UNAVAILABLE registered and emitted |
| GAP11-P1-19.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-19.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-19.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-20.01 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_ras_classification_and_reset_storm |
| GAP11-P1-20.02 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_ras_classification_and_reset_storm |
| GAP11-P1-20.03 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_failed_health_quarantines_and_excludes |
| GAP11-P1-20.04 | BLOCKED | capability validation against LIVE hardware: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build environment |
| GAP11-P1-20.05 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_ras_classification_and_reset_storm |
| GAP11-P1-20.06 | PARTIAL | bounded deadlines, exponential backoff and non-retryable classes implemented (hardware.with_retry, ScrubExecutor); no cancellation token | local evidence: 1 tes; test_hardware.ThermalHealthTests.test_failed_health_quarantines_and_excludes |
| GAP11-P1-20.07 | BLOCKED | privileged node-agent process separation not built (no hardware/OS agent to separate): BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/F |
| GAP11-P1-20.08 | PARTIAL | independent post-operation verification implemented and tested against simulators only: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/ |
| GAP11-P1-20.09 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P1-20.10 | EVIDENCED | 1 passing test(s) against simulated providers; test_hardware.ThermalHealthTests.test_ras_classification_and_reset_storm |
| GAP11-P1-20.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-20 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-20.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-20-Rnn |
| GAP11-P1-20.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-20.14 | EVIDENCED | invariants INV-RAS-1 enforced in code and asserted by tagged tests |
| GAP11-P1-20.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-20.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-20.17 | EVIDENCED | reason codes HARDWARE_FAULT registered and emitted |
| GAP11-P1-20.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-20.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-20.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-21.01 | EVIDENCED | 1 passing test(s); test_state.StoreTests.test_state_machines_reject_illegal_transitions |
| GAP11-P1-21.02 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_device_disappearance_and_reappearance |
| GAP11-P1-21.03 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_device_disappearance_and_reappearance |
| GAP11-P1-21.04 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_capability_change_under_live_lease_drains_instead_of_reshaping |
| GAP11-P1-21.05 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_device_disappearance_and_reappearance |
| GAP11-P1-21.06 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_hotplug_events_are_monotonic_time_and_recorded |
| GAP11-P1-21.07 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_device_disappearance_and_reappearance |
| GAP11-P1-21.08 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_capability_change_under_live_lease_drains_instead_of_reshaping |
| GAP11-P1-21.09 | EVIDENCED | 1 passing test(s); test_state.LifecycleAndHotplugTests.test_hotplug_events_are_monotonic_time_and_recorded |
| GAP11-P1-21.10 | PARTIAL | disk-full, partial corruption, torn tail, read-only degraded mode tested + RUNBOOK-05; quorum loss / replica restore not applicable to single-writer store: BLK-; test_hardware.InventoryTests.test_stable_identity_survives_pci_renumbering_and_replacement_is_distinguished |
| GAP11-P1-21.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-21 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-21.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-21-Rnn |
| GAP11-P1-21.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-21.14 | EVIDENCED | invariants INV-HP-1 enforced in code and asserted by tagged tests |
| GAP11-P1-21.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-21.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-21.17 | EVIDENCED | reason codes DEVICE_MISSING, AMBIGUOUS_EVIDENCE registered and emitted |
| GAP11-P1-21.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-21.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-21.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-22.01 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_victim_eligibility |
| GAP11-P1-22.02 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_victim_eligibility |
| GAP11-P1-22.03 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_victim_eligibility |
| GAP11-P1-22.04 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_preemption_feature_gate_defaults_off |
| GAP11-P1-22.05 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_allocation_is_all_or_nothing |
| GAP11-P1-22.06 | EVIDENCED | 1 passing test(s); test_scheduler.QuotaFairnessTests.test_quota_secure_default_and_caps |
| GAP11-P1-22.07 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_preemption_feature_gate_defaults_off |
| GAP11-P1-22.08 | EVIDENCED | 1 passing test(s); test_scheduler.PreemptionTests.test_victim_eligibility |
| GAP11-P1-22.09 | OPEN | no test or artifact evidences this item (component blockers: BLK-ADJ) |
| GAP11-P1-22.10 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P1-22.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-22 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-22.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-22-Rnn |
| GAP11-P1-22.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-22.14 | EVIDENCED | invariants INV-PRE-1 enforced in code and asserted by tagged tests |
| GAP11-P1-22.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-22.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-22.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-22.18 | EVIDENCED | 3 tagged tests assert refusals/fault paths |
| GAP11-P1-22.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-22.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-23.01 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P1-23.02 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P1-23.03 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P1-23.04 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_decisions_independent_of_input_order |
| GAP11-P1-23.05 | EVIDENCED | 1 passing test(s); test_scheduler.TopologyGangTests.test_gang_allocation_is_all_or_nothing |
| GAP11-P1-23.06 | EVIDENCED | 1 passing test(s); test_scheduler.QuotaFairnessTests.test_fair_queue_starvation_bound_and_backpressure |
| GAP11-P1-23.07 | OPEN | no test or artifact evidences this item |
| GAP11-P1-23.08 | OPEN | no test or artifact evidences this item |
| GAP11-P1-23.09 | EVIDENCED | 1 passing test(s); test_scheduler.ConstraintTests.test_hard_constraints_never_traded_for_score |
| GAP11-P1-23.10 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P1-23.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-23 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-23.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-23-Rnn |
| GAP11-P1-23.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-23.14 | EVIDENCED | invariants INV-CON-1 enforced in code and asserted by tagged tests |
| GAP11-P1-23.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-23.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-23.17 | EVIDENCED | reason codes CONSTRAINT_UNSATISFIED registered and emitted |
| GAP11-P1-23.18 | EVIDENCED | 3 tagged tests assert refusals/fault paths |
| GAP11-P1-23.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-23.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-24.01 | EVIDENCED | 2 passing test(s); test_observability.AuditLedgerTests.test_every_controller_mutation_is_audited_with_lineage, test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids |
| GAP11-P1-24.02 | EVIDENCED | 1 passing test(s); test_observability.AuditLedgerTests.test_chain_detects_edit_reorder_delete_and_truncation_against_witness |
| GAP11-P1-24.03 | EVIDENCED | 1 passing test(s); test_observability.AuditLedgerTests.test_every_controller_mutation_is_audited_with_lineage |
| GAP11-P1-24.04 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_histograms_counters_and_refusal_classes |
| GAP11-P1-24.05 | EVIDENCED | 2 passing test(s); test_observability.AuditLedgerTests.test_every_controller_mutation_is_audited_with_lineage, test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-24.06 | EVIDENCED | 1 passing test(s); test_observability.AuditLedgerTests.test_every_controller_mutation_is_audited_with_lineage |
| GAP11-P1-24.07 | PARTIAL | redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md) | local evidence: 1 test(s); test_observability.AuditLedgerTests.test_chain_detects_edit_reorder_delete_and_truncation_against_witness |
| GAP11-P1-24.08 | PARTIAL | dashboard specification docs/DASHBOARDS.md; not deployed: BLK-ENV: requires a provisioned multi-node deployment and real observation period | local evidence: 1 ; test_observability.MetricsLogsTraceTests.test_histograms_counters_and_refusal_classes |
| GAP11-P1-24.09 | EVIDENCED | 2 passing test(s); test_observability.AuditLedgerTests.test_chain_detects_edit_reorder_delete_and_truncation_against_witness, test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-24.10 | EVIDENCED | 2 passing test(s); test_observability.AuditLedgerTests.test_every_controller_mutation_is_audited_with_lineage, test_observability.MetricsLogsTraceTests.test_broken_subscriber_and_full_buffer_never_break_control_path |
| GAP11-P1-24.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-24 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-24.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-24-Rnn |
| GAP11-P1-24.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-24.14 | EVIDENCED | invariants INV-AUD-1 enforced in code and asserted by tagged tests |
| GAP11-P1-24.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-24.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-24.17 | EVIDENCED | reason codes STORE_CORRUPT registered and emitted |
| GAP11-P1-24.18 | EVIDENCED | 5 tagged tests assert refusals/fault paths |
| GAP11-P1-24.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-24.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-25.01 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids |
| GAP11-P1-25.02 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids |
| GAP11-P1-25.03 | EVIDENCED | 2 passing test(s); test_observability.MetricsLogsTraceTests.test_histograms_counters_and_refusal_classes, test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids |
| GAP11-P1-25.04 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_histograms_counters_and_refusal_classes |
| GAP11-P1-25.05 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV) |
| GAP11-P1-25.06 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV) |
| GAP11-P1-25.07 | PARTIAL | redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md) |
| GAP11-P1-25.08 | PARTIAL | dashboard specification docs/DASHBOARDS.md; not deployed: BLK-ENV: requires a provisioned multi-node deployment and real observation period | local evidence: 1 ; test_observability.MetricsLogsTraceTests.test_histograms_counters_and_refusal_classes |
| GAP11-P1-25.09 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV) |
| GAP11-P1-25.10 | EVIDENCED | 2 passing test(s); test_observability.MetricsLogsTraceTests.test_broken_subscriber_and_full_buffer_never_break_control_path, test_observability.MetricsLogsTraceTests.test_histograms_counters_and_refusal_classes |
| GAP11-P1-25.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-25 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-25.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-25-Rnn |
| GAP11-P1-25.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-25.14 | EVIDENCED | invariants INV-MET-1 enforced in code and asserted by tagged tests |
| GAP11-P1-25.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-25.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-25.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-25.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-25.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-25.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-26.01 | EVIDENCED | 2 passing test(s); test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids, test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-26.02 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_trace_and_request_id_propagate_end_to_end |
| GAP11-P1-26.03 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-26.04 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-26.05 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-26.06 | EVIDENCED | 1 passing test(s); test_wire.TransportTests.test_trace_and_request_id_propagate_end_to_end |
| GAP11-P1-26.07 | PARTIAL | redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md) | local evidence: 1 test(s); test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-26.08 | PARTIAL | dashboard specification docs/DASHBOARDS.md; not deployed: BLK-ENV: requires a provisioned multi-node deployment and real observation period | local evidence: 1 ; test_observability.MetricsLogsTraceTests.test_trace_context_continues_or_restarts_safely |
| GAP11-P1-26.09 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_trace_context_continues_or_restarts_safely |
| GAP11-P1-26.10 | EVIDENCED | 2 passing test(s); test_observability.MetricsLogsTraceTests.test_broken_subscriber_and_full_buffer_never_break_control_path, test_observability.MetricsLogsTraceTests.test_structured_logs_are_utc_redacted_and_sampled |
| GAP11-P1-26.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-26 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-26.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-26-Rnn |
| GAP11-P1-26.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-26.14 | EVIDENCED | invariants INV-LOG-1 enforced in code and asserted by tagged tests |
| GAP11-P1-26.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-26.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-26.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-26.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-26.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-26.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-27.01 | EVIDENCED | 2 passing test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies, test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids |
| GAP11-P1-27.02 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies |
| GAP11-P1-27.03 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies |
| GAP11-P1-27.04 | OPEN | no test or artifact evidences this item |
| GAP11-P1-27.05 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies |
| GAP11-P1-27.06 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies |
| GAP11-P1-27.07 | PARTIAL | redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md) | local evidence: 1 test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies |
| GAP11-P1-27.08 | PARTIAL | dashboard specification docs/DASHBOARDS.md; not deployed: BLK-ENV: requires a provisioned multi-node deployment and real observation period |
| GAP11-P1-27.09 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_readiness_reflects_leadership_store_and_dependencies |
| GAP11-P1-27.10 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_broken_subscriber_and_full_buffer_never_break_control_path |
| GAP11-P1-27.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-27 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-27.12 | EVIDENCED | docs/REQUIREMENTS.json: 2 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-27-Rnn |
| GAP11-P1-27.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-27.14 | EVIDENCED | invariants INV-HEALTH-1 enforced in code and asserted by tagged tests |
| GAP11-P1-27.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-27.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-27.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-27.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-27.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-27.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-28.01 | EVIDENCED | 2 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable, test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids |
| GAP11-P1-28.02 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV) |
| GAP11-P1-28.03 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-28.04 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-28.05 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-28.06 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-28.07 | PARTIAL | redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md) | local evidence: 1 test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-28.08 | PARTIAL | dashboard specification docs/DASHBOARDS.md; not deployed: BLK-ENV: requires a provisioned multi-node deployment and real observation period |
| GAP11-P1-28.09 | EVIDENCED | 1 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable |
| GAP11-P1-28.10 | EVIDENCED | 2 passing test(s); test_observability.HealthAlertTests.test_alert_rules_complete_and_actionable, test_observability.MetricsLogsTraceTests.test_broken_subscriber_and_full_buffer_never_break_control_path |
| GAP11-P1-28.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-28 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-28.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-28-Rnn |
| GAP11-P1-28.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-28.14 | EVIDENCED | invariants INV-ALERT-1 enforced in code and asserted by tagged tests |
| GAP11-P1-28.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P1-28.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-28.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-28.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P1-28.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-28.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-29.01 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_schema_validation_secure_defaults_dangerous_opt_in |
| GAP11-P1-29.02 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_schema_validation_secure_defaults_dangerous_opt_in |
| GAP11-P1-29.03 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_precedence_provenance_atomic_apply_and_rollback |
| GAP11-P1-29.04 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_precedence_provenance_atomic_apply_and_rollback |
| GAP11-P1-29.05 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_schema_validation_secure_defaults_dangerous_opt_in |
| GAP11-P1-29.06 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_precedence_provenance_atomic_apply_and_rollback |
| GAP11-P1-29.07 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_precedence_provenance_atomic_apply_and_rollback |
| GAP11-P1-29.08 | EVIDENCED | 1 passing test(s); test_security.SecretsTests.test_secret_references_resolve_through_backend_only |
| GAP11-P1-29.09 | EVIDENCED | 2 passing test(s); test_observability.AuditLedgerTests.test_chain_detects_edit_reorder_delete_and_truncation_against_witness, test_observability.ConfigTests.test_precedence_provenance_atomic_apply_and_rollback |
| GAP11-P1-29.10 | EVIDENCED | 2 passing test(s); test_observability.ConfigTests.test_concurrent_updates_are_serialised, test_observability.ConfigTests.test_schema_validation_secure_defaults_dangerous_opt_in |
| GAP11-P1-29.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-29 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-29.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-29-Rnn |
| GAP11-P1-29.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-29.14 | EVIDENCED | invariants INV-CFG-1 enforced in code and asserted by tagged tests |
| GAP11-P1-29.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-29.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-29.17 | EVIDENCED | reason codes CONFIG_INVALID registered and emitted |
| GAP11-P1-29.18 | EVIDENCED | 3 tagged tests assert refusals/fault paths |
| GAP11-P1-29.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P1-29.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-30.01 | EVIDENCED | docs/THREAT_MODEL.md trust-boundary table TB-1..TB-6 |
| GAP11-P1-30.02 | PARTIAL | HMAC workload-identity credentials verified on every state change; mutually authenticated channel (mTLS) absent: BLK-PKI: no mTLS PKI / SPIFFE issuer / GAP-06 a |
| GAP11-P1-30.03 | OPEN | no test or artifact evidences this item (component blockers: BLK-KMS) |
| GAP11-P1-30.04 | OPEN | no test or artifact evidences this item (component blockers: BLK-KMS) |
| GAP11-P1-30.05 | OPEN | no test or artifact evidences this item (component blockers: BLK-KMS) |
| GAP11-P1-30.06 | OPEN | no test or artifact evidences this item (component blockers: BLK-KMS) |
| GAP11-P1-30.07 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthnTests.test_live_key_rotation_with_overlap_and_emergency_revocation |
| GAP11-P1-30.08 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthzTests.test_sensitive_inventory_and_redaction |
| GAP11-P1-30.09 | EVIDENCED | 1 passing test(s) against simulated providers; test_security.AuthnTests.test_identity_policy_and_kms_outages_fail_closed |
| GAP11-P1-30.10 | OPEN | no test or artifact evidences this item (component blockers: BLK-KMS) |
| GAP11-P1-30.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-30 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-30.12 | EVIDENCED | docs/REQUIREMENTS.json: 4 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-30-Rnn |
| GAP11-P1-30.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-30.14 | EVIDENCED | invariants INV-SEC-1 enforced in code and asserted by tagged tests |
| GAP11-P1-30.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-30.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-30.17 | EVIDENCED | reason codes DEPENDENCY_UNAVAILABLE registered and emitted |
| GAP11-P1-30.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-30.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-30.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-31.01 | EVIDENCED | 2 passing test(s); test_observability.MetricsLogsTraceTests.test_metric_label_budget_forbids_ids, test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.02 | EVIDENCED | 1 passing test(s); test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.03 | EVIDENCED | 1 passing test(s); test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.04 | OPEN | no test or artifact evidences this item |
| GAP11-P1-31.05 | EVIDENCED | 1 passing test(s); test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.06 | EVIDENCED | 1 passing test(s); test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.07 | PARTIAL | redaction and audit integrity implemented; retention/access-control values PROPOSED only (docs/DATA_INVENTORY.md) | local evidence: 1 test(s); test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.08 | PARTIAL | dashboard specification docs/DASHBOARDS.md; not deployed: BLK-ENV: requires a provisioned multi-node deployment and real observation period |
| GAP11-P1-31.09 | EVIDENCED | 1 passing test(s); test_observability.UsageAccountingTests.test_usage_records_are_durable_and_closed_on_release |
| GAP11-P1-31.10 | EVIDENCED | 1 passing test(s); test_observability.MetricsLogsTraceTests.test_broken_subscriber_and_full_buffer_never_break_control_path |
| GAP11-P1-31.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-31 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-31.12 | EVIDENCED | docs/REQUIREMENTS.json: 2 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-31-Rnn |
| GAP11-P1-31.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-31.14 | EVIDENCED | invariants INV-USE-1 enforced in code and asserted by tagged tests |
| GAP11-P1-31.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-31.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-31.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P1-31.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P1-31.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-31.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P1-32.01 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.02 | EVIDENCED | 1 passing test(s); test_observability.ConfigTests.test_operator_drain_freeze_and_quarantine_controls |
| GAP11-P1-32.03 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.04 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.05 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.06 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.07 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.08 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.09 | EVIDENCED | 2 passing test(s); test_observability.AuditLedgerTests.test_chain_detects_edit_reorder_delete_and_truncation_against_witness, test_observability.ConfigTests.test_operator_drain_freeze_and_quarantine_controls |
| GAP11-P1-32.10 | OPEN | no test or artifact evidences this item |
| GAP11-P1-32.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P1-32 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P1-32.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P1-32-Rnn |
| GAP11-P1-32.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P1-32.14 | EVIDENCED | invariants INV-OP-1 enforced in code and asserted by tagged tests |
| GAP11-P1-32.15 | EVIDENCED | docs/DATA_INVENTORY.md |
| GAP11-P1-32.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P1-32.17 | EVIDENCED | reason codes MAINTENANCE_MODE registered and emitted |
| GAP11-P1-32.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P1-32.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P1-32.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-33.01 | EVIDENCED | 2 passing test(s); test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check, test_wire.SchemaTests.test_golden_fixtures_decode_and_reencode |
| GAP11-P2-33.02 | EVIDENCED | 2 passing test(s); test_verification.HermeticityTests.test_control_path_never_reads_wall_clock_or_unseeded_randomness_for_decisions, test_wire.SchemaTests.test_golden_fixtures_decode_and_reencode |
| GAP11-P2-33.03 | OPEN | no test or artifact evidences this item |
| GAP11-P2-33.04 | OPEN | no test or artifact evidences this item |
| GAP11-P2-33.05 | OPEN | no test or artifact evidences this item |
| GAP11-P2-33.06 | OPEN | no test or artifact evidences this item |
| GAP11-P2-33.07 | OPEN | no test or artifact evidences this item |
| GAP11-P2-33.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P2-33.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind; test_wire.SchemaTests.test_golden_fixtures_decode_and_reencode |
| GAP11-P2-33.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes |
| GAP11-P2-33.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-33 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-33.12 | EVIDENCED | docs/REQUIREMENTS.json: 2 MUST/SHOULD/MAY requirements with stable IDs GAP11-P2-33-Rnn |
| GAP11-P2-33.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P2-33.14 | EVIDENCED | invariants INV-FIX-1 enforced in code and asserted by tagged tests |
| GAP11-P2-33.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-33.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-33.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P2-33.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P2-33.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-33.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-34.01 | EVIDENCED | 1 passing test(s); test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check |
| GAP11-P2-34.02 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.03 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.04 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.05 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.06 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.07 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P2-34.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind |
| GAP11-P2-34.10 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-34 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-34.12 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.13 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.14 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.15 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-34.17 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.18 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.19 | BLOCKED | BLK-ADJ: adjacent GAP-02/06/09/10 services and workload runtime are not available to integrate |
| GAP11-P2-34.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-35.01 | EVIDENCED | 1 passing test(s); test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check |
| GAP11-P2-35.02 | EVIDENCED | 1 passing test(s); test_verification.HermeticityTests.test_control_path_never_reads_wall_clock_or_unseeded_randomness_for_decisions |
| GAP11-P2-35.03 | EVIDENCED | 1 passing test(s); test_wire.SchemaTests.test_decoder_fuzz_never_raises_untyped |
| GAP11-P2-35.04 | OPEN | no test or artifact evidences this item |
| GAP11-P2-35.05 | OPEN | no test or artifact evidences this item |
| GAP11-P2-35.06 | OPEN | no test or artifact evidences this item |
| GAP11-P2-35.07 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P2-35.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline | local evidence: 1 test(s); test_wire.SchemaTests.test_decoder_fuzz_never_raises_untyped |
| GAP11-P2-35.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind |
| GAP11-P2-35.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes |
| GAP11-P2-35.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-35 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-35.12 | EVIDENCED | docs/REQUIREMENTS.json: 2 MUST/SHOULD/MAY requirements with stable IDs GAP11-P2-35-Rnn |
| GAP11-P2-35.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P2-35.14 | EVIDENCED | invariants INV-FUZZ-1 enforced in code and asserted by tagged tests |
| GAP11-P2-35.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-35.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-35.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P2-35.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P2-35.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-35.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-36.01 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_barrier_collisions_allocate_release_scrub_reconcile_failover |
| GAP11-P2-36.02 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_barrier_collisions_allocate_release_scrub_reconcile_failover |
| GAP11-P2-36.03 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_soak_many_threads_idempotent_retries |
| GAP11-P2-36.04 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_partitioned_old_leader_with_delayed_messages_cannot_double_allocate |
| GAP11-P2-36.05 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_barrier_collisions_allocate_release_scrub_reconcile_failover |
| GAP11-P2-36.06 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV) |
| GAP11-P2-36.07 | EVIDENCED | 1 passing test(s); test_scheduler.AdversarialTests.test_randomised_contention_preserves_invariants |
| GAP11-P2-36.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P2-36.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind; test_verification.SplitBrainTests.test_soak_many_threads_idempotent_retries |
| GAP11-P2-36.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes |
| GAP11-P2-36.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-36 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-36.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P2-36-Rnn |
| GAP11-P2-36.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P2-36.14 | EVIDENCED | invariants INV-CONC-1 enforced in code and asserted by tagged tests |
| GAP11-P2-36.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-36.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-36.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P2-36.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P2-36.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-36.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-37.01 | EVIDENCED | 1 passing test(s); test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check |
| GAP11-P2-37.02 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P2-37.03 | EVIDENCED | 1 passing test(s); test_security.AuthnTests.test_forged_expired_replayed_and_wrong_audience_credentials_refused |
| GAP11-P2-37.04 | EVIDENCED | 1 passing test(s); test_security.AuthzTests.test_confused_deputy_and_cross_tenant_release_through_the_service |
| GAP11-P2-37.05 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P2-37.06 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P2-37.07 | OPEN | no test or artifact evidences this item (component blockers: BLK-HW) |
| GAP11-P2-37.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P2-37.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind |
| GAP11-P2-37.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes |
| GAP11-P2-37.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-37 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-37.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P2-37-Rnn |
| GAP11-P2-37.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P2-37.14 | EVIDENCED | invariants INV-ADV-1 enforced in code and asserted by tagged tests |
| GAP11-P2-37.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-37.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-37.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P2-37.18 | EVIDENCED | 2 tagged tests assert refusals/fault paths |
| GAP11-P2-37.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-37.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-38.01 | EVIDENCED | 2 passing test(s); test_verification.FaultMatrixTests.test_fault_matrix, test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check |
| GAP11-P2-38.02 | EVIDENCED | 1 passing test(s); test_verification.FaultMatrixTests.test_fault_matrix |
| GAP11-P2-38.03 | EVIDENCED | 1 passing test(s); test_verification.FaultMatrixTests.test_fault_matrix |
| GAP11-P2-38.04 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_partitioned_old_leader_with_delayed_messages_cannot_double_allocate |
| GAP11-P2-38.05 | EVIDENCED | 1 passing test(s); test_verification.FaultMatrixTests.test_fault_matrix |
| GAP11-P2-38.06 | EVIDENCED | 1 passing test(s); test_verification.SplitBrainTests.test_partitioned_old_leader_with_delayed_messages_cannot_double_allocate |
| GAP11-P2-38.07 | EVIDENCED | 1 passing test(s); test_verification.FaultMatrixTests.test_fault_matrix |
| GAP11-P2-38.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P2-38.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind |
| GAP11-P2-38.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes; test_verification.FaultMatrixTests.test_fault_matrix |
| GAP11-P2-38.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-38 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-38.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P2-38-Rnn |
| GAP11-P2-38.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P2-38.14 | EVIDENCED | invariants INV-FAULT-1 enforced in code and asserted by tagged tests |
| GAP11-P2-38.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-38.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-38.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P2-38.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths |
| GAP11-P2-38.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-38.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-39.01 | EVIDENCED | 2 passing test(s); test_verification.BenchmarkTests.test_latency_thresholds_local_reference_host, test_verification.HermeticityTests.test_every_test_is_tagged_and_every_tag_is_a_real_check |
| GAP11-P2-39.02 | EVIDENCED | 1 passing test(s); test_verification.BenchmarkTests.test_latency_thresholds_local_reference_host |
| GAP11-P2-39.03 | EVIDENCED | 1 passing test(s); test_verification.BenchmarkTests.test_latency_thresholds_local_reference_host |
| GAP11-P2-39.04 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV; BLK-HUMAN) |
| GAP11-P2-39.05 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV; BLK-HUMAN) |
| GAP11-P2-39.06 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV; BLK-HUMAN) |
| GAP11-P2-39.07 | OPEN | no test or artifact evidences this item (component blockers: BLK-ENV; BLK-HUMAN) |
| GAP11-P2-39.08 | PARTIAL | seeded mutation fuzzing over a retained fixture corpus (gap11_control/tests/fixtures); no crash-to-regression promotion pipeline |
| GAP11-P2-39.09 | PARTIAL | latency thresholds PROPOSED and enforced in-test; soak/coverage/flaky-rate thresholds unapproved: BLK-HUMAN: requires a named accountable owner / approver / ind; test_verification.BenchmarkTests.test_latency_thresholds_local_reference_host |
| GAP11-P2-39.10 | EVIDENCED | evidence/RUN.json: source digest, environment fingerprint, seeds, per-test outcomes; test_verification.BenchmarkTests.test_latency_thresholds_local_reference_host |
| GAP11-P2-39.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-39 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-39.12 | PARTIAL | only the capability MUST (GAP11-P2-39-R00); no component invariants |
| GAP11-P2-39.13 | PARTIAL | typed inputs/outputs + PK_ERROR/1 codes with retryability (wire.RETRYABLE); timeouts/retry/idempotency specified; client cancellation not implemented (EXC-008) |
| GAP11-P2-39.14 | OPEN | no invariants |
| GAP11-P2-39.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-39.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-39.17 | PARTIAL | uses shared Telemetry/Metrics but defines no component-specific reason code |
| GAP11-P2-39.18 | OPEN | no tagged negative test |
| GAP11-P2-39.19 | EVIDENCED | docs/ROLLOUT.md + RUNBOOK-02/03 + docs/COMPATIBILITY.md mixed-version rules |
| GAP11-P2-39.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-40.01 | EVIDENCED | pyproject.toml (name, version, requires-python, build backend); licence UNSPECIFIED is stated, not invented |
| GAP11-P2-40.02 | OPEN |  |
| GAP11-P2-40.03 | EVIDENCED | deterministic source archive built twice, identical sha256 0a532141b403e38f… |
| GAP11-P2-40.04 | EVIDENCED | release/SBOM.cdx.json (CycloneDX 1.5; per-file SHA-256; no vendored/native code) |
| GAP11-P2-40.05 | BLOCKED | BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-40.06 | BLOCKED | clean-install/upgrade/downgrade/uninstall matrix needs every supported platform: BLK-ENV: requires a provisioned multi-node deployment and real observation peri |
| GAP11-P2-40.07 | EVIDENCED | residue scan: no __pycache__/.pyc/private keys/tokens in the tree |
| GAP11-P2-40.08 | PARTIAL | docs/COMPATIBILITY.md; hardware/driver/firmware rows untested: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build en |
| GAP11-P2-40.09 | PARTIAL | ci.sh gates compile + all tests + benchmark thresholds + manifest; vulnerability/licence/provenance gates absent (no licence chosen, BLK-SIGN: release signing k |
| GAP11-P2-40.10 | PARTIAL | MANIFEST.sha256, SBOM, CHANGELOG, rollback in RUNBOOK-03 retained; no signatures/provenance: BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-40.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-40 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-40.12 | PARTIAL | only the capability MUST (GAP11-P2-40-R00); no component invariants |
| GAP11-P2-40.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-40.14 | OPEN | no invariants |
| GAP11-P2-40.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-40.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-40.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-40.18 | OPEN | no tagged negative test |
| GAP11-P2-40.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-40.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-41.01 | EVIDENCED | pyproject.toml (name, version, requires-python, build backend); licence UNSPECIFIED is stated, not invented |
| GAP11-P2-41.02 | OPEN |  |
| GAP11-P2-41.03 | EVIDENCED | deterministic source archive built twice, identical sha256 0a532141b403e38f… |
| GAP11-P2-41.04 | EVIDENCED | release/SBOM.cdx.json (CycloneDX 1.5; per-file SHA-256; no vendored/native code) |
| GAP11-P2-41.05 | BLOCKED | BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-41.06 | BLOCKED | clean-install/upgrade/downgrade/uninstall matrix needs every supported platform: BLK-ENV: requires a provisioned multi-node deployment and real observation peri |
| GAP11-P2-41.07 | EVIDENCED | residue scan: no __pycache__/.pyc/private keys/tokens in the tree |
| GAP11-P2-41.08 | PARTIAL | docs/COMPATIBILITY.md; hardware/driver/firmware rows untested: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build en |
| GAP11-P2-41.09 | PARTIAL | ci.sh gates compile + all tests + benchmark thresholds + manifest; vulnerability/licence/provenance gates absent (no licence chosen, BLK-SIGN: release signing k |
| GAP11-P2-41.10 | PARTIAL | MANIFEST.sha256, SBOM, CHANGELOG, rollback in RUNBOOK-03 retained; no signatures/provenance: BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-41.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-41 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-41.12 | PARTIAL | only the capability MUST (GAP11-P2-41-R00); no component invariants |
| GAP11-P2-41.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-41.14 | OPEN | no invariants |
| GAP11-P2-41.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-41.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-41.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-41.18 | OPEN | no tagged negative test |
| GAP11-P2-41.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-41.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-42.01 | EVIDENCED | pyproject.toml (name, version, requires-python, build backend); licence UNSPECIFIED is stated, not invented |
| GAP11-P2-42.02 | OPEN |  |
| GAP11-P2-42.03 | EVIDENCED | deterministic source archive built twice, identical sha256 0a532141b403e38f… |
| GAP11-P2-42.04 | EVIDENCED | release/SBOM.cdx.json (CycloneDX 1.5; per-file SHA-256; no vendored/native code) |
| GAP11-P2-42.05 | BLOCKED | BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-42.06 | BLOCKED | clean-install/upgrade/downgrade/uninstall matrix needs every supported platform: BLK-ENV: requires a provisioned multi-node deployment and real observation peri |
| GAP11-P2-42.07 | EVIDENCED | residue scan: no __pycache__/.pyc/private keys/tokens in the tree |
| GAP11-P2-42.08 | PARTIAL | docs/COMPATIBILITY.md; hardware/driver/firmware rows untested: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build en |
| GAP11-P2-42.09 | PARTIAL | ci.sh gates compile + all tests + benchmark thresholds + manifest; vulnerability/licence/provenance gates absent (no licence chosen, BLK-SIGN: release signing k |
| GAP11-P2-42.10 | PARTIAL | MANIFEST.sha256, SBOM, CHANGELOG, rollback in RUNBOOK-03 retained; no signatures/provenance: BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-42.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-42 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-42.12 | PARTIAL | only the capability MUST (GAP11-P2-42-R00); no component invariants |
| GAP11-P2-42.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-42.14 | OPEN | no invariants |
| GAP11-P2-42.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-42.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-42.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-42.18 | OPEN | no tagged negative test |
| GAP11-P2-42.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-42.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-43.01 | EVIDENCED | pyproject.toml (name, version, requires-python, build backend); licence UNSPECIFIED is stated, not invented |
| GAP11-P2-43.02 | OPEN |  |
| GAP11-P2-43.03 | EVIDENCED | deterministic source archive built twice, identical sha256 0a532141b403e38f… |
| GAP11-P2-43.04 | EVIDENCED | release/SBOM.cdx.json (CycloneDX 1.5; per-file SHA-256; no vendored/native code) |
| GAP11-P2-43.05 | BLOCKED | BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-43.06 | BLOCKED | clean-install/upgrade/downgrade/uninstall matrix needs every supported platform: BLK-ENV: requires a provisioned multi-node deployment and real observation peri |
| GAP11-P2-43.07 | EVIDENCED | residue scan: no __pycache__/.pyc/private keys/tokens in the tree |
| GAP11-P2-43.08 | PARTIAL | docs/COMPATIBILITY.md; hardware/driver/firmware rows untested: BLK-HW: no accelerator hardware or vendor SDK (NVML/ROCm SMI/Level Zero/FPGA/NPU) in the build en |
| GAP11-P2-43.09 | PARTIAL | ci.sh gates compile + all tests + benchmark thresholds + manifest; vulnerability/licence/provenance gates absent (no licence chosen, BLK-SIGN: release signing k |
| GAP11-P2-43.10 | PARTIAL | MANIFEST.sha256, SBOM, CHANGELOG, rollback in RUNBOOK-03 retained; no signatures/provenance: BLK-SIGN: release signing keys and custody policy do not exist |
| GAP11-P2-43.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-43 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-43.12 | PARTIAL | only the capability MUST (GAP11-P2-43-R00); no component invariants |
| GAP11-P2-43.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-43.14 | OPEN | no invariants |
| GAP11-P2-43.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-43.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-43.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-43.18 | OPEN | no tagged negative test |
| GAP11-P2-43.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-43.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-44.01 | PARTIAL | docs/THREAT_MODEL.md: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / indepe |
| GAP11-P2-44.02 | EVIDENCED | docs/THREAT_MODEL.md states scope/non-goals |
| GAP11-P2-44.03 | EVIDENCED | RR-01..RR-05 |
| GAP11-P2-44.04 | EVIDENCED | stable identifiers `THR-…` in docs/THREAT_MODEL.md |
| GAP11-P2-44.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-44.06 | PARTIAL | review cadence + out-of-cycle triggers; no expiry |
| GAP11-P2-44.07 | EVIDENCED | each THR-xx row names its mitigation and test evidence |
| GAP11-P2-44.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-44.09 | PARTIAL | v4.2.0 artifacts retained; no supersession header |
| GAP11-P2-44.10 | PARTIAL | completion gate implied by GAP11-EXIT-*, not stated in the artifact |
| GAP11-P2-44.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-44 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-44.12 | PARTIAL | only the capability MUST (GAP11-P2-44-R00); no component invariants |
| GAP11-P2-44.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-44.14 | OPEN | no invariants |
| GAP11-P2-44.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-44.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-44.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-44.18 | OPEN | no tagged negative test |
| GAP11-P2-44.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-44.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-45.01 | PARTIAL | docs/ADR-001-control-plane.md: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver |
| GAP11-P2-45.02 | EVIDENCED | docs/ADR-001-control-plane.md states scope/non-goals |
| GAP11-P2-45.03 | EVIDENCED | docs/ADR-001-control-plane.md trade-offs / established facts |
| GAP11-P2-45.04 | EVIDENCED | stable identifiers `DEC-…` in docs/ADR-001-control-plane.md |
| GAP11-P2-45.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-45.06 | OPEN | no expiry/revalidation rule in this artifact |
| GAP11-P2-45.07 | PARTIAL | references to runbooks/tests are partial |
| GAP11-P2-45.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-45.09 | EVIDENCED | ADR carries Supersedes/Superseded-by; v4.2.0 AUDIT_REPORT.md retained unchanged |
| GAP11-P2-45.10 | PARTIAL | completion gate implied by GAP11-EXIT-*, not stated in the artifact |
| GAP11-P2-45.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-45 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-45.12 | PARTIAL | only the capability MUST (GAP11-P2-45-R00); no component invariants |
| GAP11-P2-45.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-45.14 | OPEN | no invariants |
| GAP11-P2-45.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-45.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-45.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-45.18 | OPEN | no tagged negative test |
| GAP11-P2-45.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-45.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-46.01 | PARTIAL | docs/OWNERSHIP.md: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independe |
| GAP11-P2-46.02 | PARTIAL | roles listed, none assigned |
| GAP11-P2-46.03 | OPEN | no assumptions section in this artifact |
| GAP11-P2-46.04 | OPEN | no identifiers (no owner yet) |
| GAP11-P2-46.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.06 | OPEN | no expiry/revalidation rule in this artifact |
| GAP11-P2-46.07 | PARTIAL | references to runbooks/tests are partial |
| GAP11-P2-46.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-46.09 | PARTIAL | v4.2.0 artifacts retained; no supersession header |
| GAP11-P2-46.10 | EVIDENCED | docs/OWNERSHIP.md states the exact evidence required to close |
| GAP11-P2-46.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-46 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-46.12 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.13 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.14 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.15 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-46.17 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.18 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.19 | BLOCKED | BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-46.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-47.01 | PARTIAL | docs/RUNBOOKS.md: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independen |
| GAP11-P2-47.02 | EVIDENCED | docs/RUNBOOKS.md states scope/non-goals |
| GAP11-P2-47.03 | OPEN | no assumptions section in this artifact |
| GAP11-P2-47.04 | EVIDENCED | stable identifiers `RUNBOOK-…` in docs/RUNBOOKS.md |
| GAP11-P2-47.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-47.06 | OPEN | no expiry/revalidation rule in this artifact |
| GAP11-P2-47.07 | PARTIAL | references to runbooks/tests are partial |
| GAP11-P2-47.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-47.09 | PARTIAL | v4.2.0 artifacts retained; no supersession header |
| GAP11-P2-47.10 | PARTIAL | completion gate implied by GAP11-EXIT-*, not stated in the artifact |
| GAP11-P2-47.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-47 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-47.12 | PARTIAL | only the capability MUST (GAP11-P2-47-R00); no component invariants |
| GAP11-P2-47.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-47.14 | OPEN | no invariants |
| GAP11-P2-47.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-47.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-47.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-47.18 | OPEN | no tagged negative test |
| GAP11-P2-47.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-47.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-48.01 | PARTIAL | docs/EXCEPTIONS.json: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / indepe |
| GAP11-P2-48.02 | EVIDENCED | docs/EXCEPTIONS.json states scope/non-goals |
| GAP11-P2-48.03 | OPEN | no assumptions section in this artifact |
| GAP11-P2-48.04 | EVIDENCED | stable identifiers `EXC-…` in docs/EXCEPTIONS.json |
| GAP11-P2-48.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-48.06 | EVIDENCED | every exception carries expires + revalidate |
| GAP11-P2-48.07 | PARTIAL | references to runbooks/tests are partial |
| GAP11-P2-48.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-48.09 | PARTIAL | v4.2.0 artifacts retained; no supersession header |
| GAP11-P2-48.10 | PARTIAL | completion gate implied by GAP11-EXIT-*, not stated in the artifact |
| GAP11-P2-48.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-48 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-48.12 | PARTIAL | only the capability MUST (GAP11-P2-48-R00); no component invariants |
| GAP11-P2-48.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-48.14 | OPEN | no invariants |
| GAP11-P2-48.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-48.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-48.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-48.18 | OPEN | no tagged negative test |
| GAP11-P2-48.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-48.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-49.01 | PARTIAL | docs/MASTER_MD_DISPOSITION.md: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver |
| GAP11-P2-49.02 | EVIDENCED | docs/MASTER_MD_DISPOSITION.md states scope/non-goals |
| GAP11-P2-49.03 | EVIDENCED | docs/MASTER_MD_DISPOSITION.md trade-offs / established facts |
| GAP11-P2-49.04 | EVIDENCED | stable identifiers `GAP11-EXIT-09…` in docs/MASTER_MD_DISPOSITION.md |
| GAP11-P2-49.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-49.06 | OPEN | no expiry/revalidation rule in this artifact |
| GAP11-P2-49.07 | PARTIAL | references to runbooks/tests are partial |
| GAP11-P2-49.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-49.09 | PARTIAL | v4.2.0 artifacts retained; no supersession header |
| GAP11-P2-49.10 | EVIDENCED | docs/MASTER_MD_DISPOSITION.md states the exact evidence required to close |
| GAP11-P2-49.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-49 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-49.12 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.13 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.14 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.15 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-49.17 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.18 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.19 | BLOCKED | BLK-MASTER: the source-series MASTER.md is absent from every supplied artifact; BLK-HUMAN: requires a named accountable owner / approver / independent reviewer  |
| GAP11-P2-49.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
| GAP11-P2-50.01 | PARTIAL | evidence/EXIT_BUNDLE.json: cadence/triggers stated where applicable; owner and approver UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / i |
| GAP11-P2-50.02 | EVIDENCED | evidence/EXIT_BUNDLE.json states scope/non-goals |
| GAP11-P2-50.03 | OPEN | no assumptions section in this artifact |
| GAP11-P2-50.04 | EVIDENCED | stable identifiers `GAP11-EXIT-…` in evidence/EXIT_BUNDLE.json |
| GAP11-P2-50.05 | BLOCKED | no dated approval or owner acknowledgement exists: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assigned) |
| GAP11-P2-50.06 | OPEN | no expiry/revalidation rule in this artifact |
| GAP11-P2-50.07 | EVIDENCED | docs/TRACEABILITY.md links every check to tests/artifacts |
| GAP11-P2-50.08 | EVIDENCED | versioned inside the 4.3.0 package alongside the code |
| GAP11-P2-50.09 | PARTIAL | v4.2.0 artifacts retained; no supersession header |
| GAP11-P2-50.10 | EVIDENCED | evidence/EXIT_BUNDLE.json states the exact evidence required to close |
| GAP11-P2-50.11 | PARTIAL | docs/DESIGN_RECORDS.md#GAP11-P2-50 (all fields present); owner UNASSIGNED: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none |
| GAP11-P2-50.12 | EVIDENCED | docs/REQUIREMENTS.json: 3 MUST/SHOULD/MAY requirements with stable IDs GAP11-P2-50-Rnn |
| GAP11-P2-50.13 | PARTIAL | artifact interface = file format; failure contract n/a |
| GAP11-P2-50.14 | EVIDENCED | invariants INV-EXIT-1 enforced in code and asserted by tagged tests; test_verification.ExitGateFalsifierTests.test_exit_gates_go_only_when_every_input_holds |
| GAP11-P2-50.15 | EVIDENCED | docs/DATA_INVENTORY.md (declares no persistent datum) |
| GAP11-P2-50.16 | EVIDENCED | docs/OPERATING_MODES.md |
| GAP11-P2-50.17 | BLOCKED | not applicable to a document; exception EXC-005 PROPOSED, unapproved: BLK-HUMAN: requires a named accountable owner / approver / independent reviewer (none assi |
| GAP11-P2-50.18 | EVIDENCED | 1 tagged tests assert refusals/fault paths; test_verification.ExitGateFalsifierTests.test_exit_gates_go_only_when_every_input_holds |
| GAP11-P2-50.19 | PARTIAL | global rollout rules only (docs/ROLLOUT.md header) |
| GAP11-P2-50.20 | BLOCKED | acceptance needs design approval + independent security review + operator sign-off: BLK-HUMAN: requires a named accountable owner / approver / independent revie |
