# INV-52 Requirements Traceability Matrix

Generated from `governance/requirements.json` (91 rows). Status vocabulary:

* **IMPLEMENTED** — Checklist-complete: implementation + tests + deployed evidence + owner/reviewer approval (none yet)
* **EVIDENCED_LOCAL** — Implementation and automated tests pass in this repository; awaiting independent review and deployed evidence
* **DOCUMENTED** — Normative artifact exists and is linked; awaiting approval and (where applicable) execution
* **BLOCKED** — Cannot be completed without an external input named in blockers

| ID | Was | Status | Artifacts | Tests | Blockers / waivers |
|---|---|---|---|---|---|
| INV-52-C003 | Partial | DOCUMENTED | `docs/SCOPE.md`<br>`governance/dependencies.json` | `test_governance.py::test_core_has_no_ambient_authority` |  |
| INV-52-C005 | Partial | DOCUMENTED | `docs/SCOPE.md` | `test_security.py::test_key_provider_or_clock_outage_denies`<br>`test_resilience_config.py::test_bootstrap_refuses_ready_when_critical_dependency_down` |  |
| INV-52-C008 | Partial | DOCUMENTED | `docs/SCOPE.md` | `test_resilience_config.py::test_validation_catches_every_class` |  |
| INV-52-C009 | Missing | BLOCKED | `OWNERS.md`<br>`CODEOWNERS`<br>`governance/owners.json` | `test_governance.py::test_owners_schema_and_roles` | organisation must name accountable owner, deputy, security, release, on-call and reviewers |
| INV-52-C010 | Missing | BLOCKED | `docs/adr/ADR-0001-messaging-abstraction-dapr-pubsub.md` |  | ADR is PROPOSED; approval by owner + architecture reviewer required |
| INV-52-C011 | Partial | EVIDENCED_LOCAL | `docs/REQUIREMENTS.md`<br>`examples/fixtures/conformance.json` | `test_integration.py::test_fixture_suite`<br>`test_runtime_ext.py::test_every_route_has_a_reason` |  |
| INV-52-C012 | Missing | DOCUMENTED | `docs/REQUIREMENTS.md`<br>`examples/config/site.edge-1.json` | `test_governance.py::test_config_defaults_and_examples_match_schema`<br>`test_integration.py::test_offline_queue_reconnect_in_order_no_loss_no_dup` |  |
| INV-52-C013 | Partial | DOCUMENTED | `docs/REQUIREMENTS.md`<br>`perf/baseline.json` |  |  |
| INV-52-C014 | Missing | EVIDENCED_LOCAL | `docs/REQUIREMENTS.md`<br>`runtime.py`<br>`schemas/PK_MSG_DECISION_1.schema.json` | `test_runtime_ext.py::test_payload_size_limit_rejects_and_records_terminal`<br>`test_runtime_ext.py::test_freeze_is_retryable_disable_is_terminal`<br>`test_runtime_ext.py::test_every_route_has_a_reason`<br>`test_runtime_ext.py::test_duplicate_id_suppressed_within_window` |  |
| INV-52-C015 | Missing | EVIDENCED_LOCAL | `lifecycle.py`<br>`runtime.py`<br>`docs/REQUIREMENTS.md` | `test_resilience_config.py::test_legal_and_illegal_transitions`<br>`test_runtime_ext.py::test_every_declared_transition_is_legal_and_others_are_not` |  |
| INV-52-C017 | Partial | EVIDENCED_LOCAL | `resilience.py`<br>`docs/REQUIREMENTS.md` | `test_resilience_config.py::test_per_app_fairness`<br>`test_resilience_config.py::test_key_table_bounded`<br>`test_runtime_ext.py::test_topic_limit` |  |
| INV-52-C018 | Missing | EVIDENCED_LOCAL | `adapters.py`<br>`docs/REQUIREMENTS.md` | `test_integration.py::test_offline_queue_reconnect_in_order_no_loss_no_dup`<br>`test_integration.py::test_capacity_is_backpressure_not_growth`<br>`test_integration.py::test_expiry_bounds_offline_age` |  |
| INV-52-C019 | Missing | DOCUMENTED | `docs/REQUIREMENTS.md` |  |  |
| INV-52-C020 | Missing | EVIDENCED_LOCAL | `governance/requirements.json`<br>`governance/RTM.md`<br>`gate.py` | `test_governance.py::test_rtm_consistent_and_covers_all_91_unresolved` |  |
| INV-52-C021 | Partial | DOCUMENTED | `docs/INTERFACES.md` | `test_governance.py::test_every_error_code_is_documented` |  |
| INV-52-C022 | Partial | EVIDENCED_LOCAL | `schemas.py`<br>`schemas/PK_MSG_PUBLISH_1.schema.json`<br>`schemas/PK_MSG_CONFIG_1.schema.json` | `test_governance.py::test_every_supported_contract_has_a_schema_file`<br>`test_governance.py::test_decisions_and_health_match_schema`<br>`test_governance.py::test_publish_request_and_envelope_schema` |  |
| INV-52-C023 | Partial | EVIDENCED_LOCAL | `security.py`<br>`docs/INTERFACES.md` | `test_security.py::test_forged_expired_replayed_malformed_tokens_denied`<br>`test_security.py::test_valid_token_publishes` |  |
| INV-52-C024 | Partial | EVIDENCED_LOCAL | `security.py`<br>`docs/INTERFACES.md` | `test_security.py::test_least_privilege_nothing_by_default_and_revocation`<br>`test_security.py::test_tenants_cannot_cross` |  |
| INV-52-C025 | Missing | EVIDENCED_LOCAL | `resilience.py`<br>`docs/INTERFACES.md` | `test_resilience_config.py::test_deadline_and_cancellation`<br>`test_resilience_config.py::test_never_retries_non_idempotent_or_terminal`<br>`test_runtime_ext.py::test_duplicate_id_suppressed_within_window`<br>`test_integration.py::test_capacity_is_backpressure_not_growth` |  |
| INV-52-C027 | Partial | EVIDENCED_LOCAL | `schemas.py`<br>`docs/COMPATIBILITY.md` | `test_integration.py::test_negotiation`<br>`test_integration.py::test_forward_compatible_unknown_optional_fields_accepted` |  |
| INV-52-C028 | Partial | EVIDENCED_LOCAL | `docs/INTERFACES.md`<br>`runtime.py` | `test_runtime_ext.py::test_payload_size_limit_rejects_and_records_terminal`<br>`test_runtime_ext.py::test_payload_at_limit_boundary_is_accepted`<br>`test_runtime_ext.py::test_nesting_limit`<br>`test_governance.py::test_documented_limits_match_code` |  |
| INV-52-C029 | Partial | EVIDENCED_LOCAL | `examples/fixtures/conformance.json`<br>`examples/basic.py` | `test_integration.py::test_fixture_suite` |  |
| INV-52-C030 | Missing | BLOCKED | `adapters.py` | `test_integration.py::test_publish_structured_cloudevent`<br>`test_integration.py::test_inbound_delivery_status_mapping` | tested against an in-process Dapr HTTP emulator only; live daprd + INV-46/INV-53 integration environment required |
| INV-52-C031 | Missing | BLOCKED | `docs/COMPATIBILITY.md`<br>`tools/sbom.py` |  | Dapr 1.17.x is a candidate; exact version pin needs ADR approval; sibling INV-46 pins out-of-support 1.14.4 |
| INV-52-C032 | Missing | DOCUMENTED | `docs/CONFIGURATION.md` |  |  |
| INV-52-C033 | Missing | EVIDENCED_LOCAL | `config.py`<br>`schemas/PK_MSG_CONFIG_1.schema.json` | `test_resilience_config.py::test_defaults_are_secure_and_valid`<br>`test_governance.py::test_config_defaults_and_examples_match_schema` |  |
| INV-52-C034 | Partial | EVIDENCED_LOCAL | `config.py` | `test_resilience_config.py::test_validation_catches_every_class`<br>`test_resilience_config.py::test_activation_is_atomic_and_invalid_keeps_previous` |  |
| INV-52-C035 | Partial | EVIDENCED_LOCAL | `config.py`<br>`examples/config/env.prod.json`<br>`examples/config/site.edge-1.json` | `test_resilience_config.py::test_overlays_replace_lists_and_merge_maps`<br>`test_governance.py::test_config_defaults_and_examples_match_schema` |  |
| INV-52-C036 | Missing | EVIDENCED_LOCAL | `config.py` | `test_resilience_config.py::test_provenance_recorded` |  |
| INV-52-C037 | Partial | EVIDENCED_LOCAL | `config.py` | `test_resilience_config.py::test_no_partial_state_visible_during_activation`<br>`test_resilience_config.py::test_activation_is_atomic_and_invalid_keeps_previous` |  |
| INV-52-C038 | Missing | EVIDENCED_LOCAL | `config.py`<br>`docs/OPERATIONS.md` | `test_resilience_config.py::test_subscriptions_survive_activation_and_rollback`<br>`test_resilience_config.py::test_automatic_rollback_on_failed_health_check`<br>`test_resilience_config.py::test_rollback_without_history` |  |
| INV-52-C039 | Partial | EVIDENCED_LOCAL | `security.py`<br>`config.py`<br>`deploy/dapr/pubsub-component.yaml` | `test_resilience_config.py::test_validation_catches_every_class`<br>`test_security.py::test_find_secrets`<br>`test_governance.py::test_deploy_manifests_have_no_inline_secrets_and_match_library_defaults` |  |
| INV-52-C040 | Partial | EVIDENCED_LOCAL | `lifecycle.py`<br>`__main__.py`<br>`docs/OPERATIONS.md` | `test_resilience_config.py::test_bootstrap_to_ready_and_emergency_disable`<br>`test_resilience_config.py::test_bootstrap_refuses_ready_when_critical_dependency_down` |  |
| INV-52-C041 | Partial | BLOCKED | `docs/THREAT_MODEL.md`<br>`governance/threats.json` | `test_governance.py::test_threat_map_tests_exist` | independent security review required; T17/T18 enforced by platform |
| INV-52-C042 | Partial | EVIDENCED_LOCAL | `security.py` | `test_security.py::test_least_privilege_nothing_by_default_and_revocation` |  |
| INV-52-C043 | Partial | EVIDENCED_LOCAL | `runtime.py`<br>`docs/SECURITY.md` | `test_governance.py::test_core_has_no_ambient_authority` |  |
| INV-52-C044 | Missing | BLOCKED | `security.py` | `test_security.py::test_forged_expired_replayed_malformed_tokens_denied`<br>`test_security.py::test_artifact_admission` | node/peer/control-plane attestation needs the platform IdP; waiver W-001<br>waiver W-001 |
| INV-52-C045 | Missing | BLOCKED | `security.py` | `test_security.py::test_artifact_admission` | signature verification (Sigstore/cosign) not implemented; waiver W-001<br>waiver W-001 |
| INV-52-C046 | Missing | EVIDENCED_LOCAL | `security.py` | `test_security.py::test_tenants_cannot_cross`<br>`test_security.py::test_dead_letters_are_tenant_scoped`<br>`test_security.py::test_namespace_separator_injection_refused` |  |
| INV-52-C047 | Missing | BLOCKED | `docs/SECURITY.md`<br>`deploy/dapr/pubsub-component.yaml` |  | transport mTLS (Dapr Sentry), broker TLS and at-rest encryption with KMS rotation are external; no evidence available |
| INV-52-C048 | Missing | EVIDENCED_LOCAL | `lifecycle.py`<br>`security.py` | `test_security.py::test_key_provider_or_clock_outage_denies`<br>`test_resilience_config.py::test_security_dependency_outage_fails_closed_noncritical_degrades` |  |
| INV-52-C049 | Missing | EVIDENCED_LOCAL | `security.py` | `test_security.py::test_denials_and_accepts_are_chained_and_verifiable`<br>`test_security.py::test_tamper_reorder_and_truncation_detected` |  |
| INV-52-C050 | Partial | EVIDENCED_LOCAL | `tests/test_adversarial.py` | `test_adversarial.py::test_replay_of_captured_token_and_cross_tenant_token`<br>`test_adversarial.py::test_predicate_cannot_escalate_by_mutating_policy_through_message`<br>`test_adversarial.py::test_json_nesting_bomb_rejected_without_recursion_error` |  |
| INV-52-C051 | Partial | DOCUMENTED | `docs/RELIABILITY.md` | `test_runtime.py::test_routing_dead_letter_and_predicate_isolation`<br>`test_integration.py::test_partition_of_one_topic_does_not_block_other_topics_directly` | waiver W-006 |
| INV-52-C052 | Missing | EVIDENCED_LOCAL | `runtime.py`<br>`lifecycle.py`<br>`docs/RELIABILITY.md` | `test_runtime_ext.py::test_health_degrades_on_backlog_and_stall` |  |
| INV-52-C053 | Partial | EVIDENCED_LOCAL | `resilience.py`<br>`deploy/dapr/resiliency.yaml` | `test_resilience_config.py::test_retries_retryable_idempotent_then_succeeds`<br>`test_resilience_config.py::test_bounded_attempts_and_jitter_cap`<br>`test_integration.py::test_retry_on_503_then_success_and_terminal_on_403` |  |
| INV-52-C054 | Partial | EVIDENCED_LOCAL | `resilience.py` | `test_resilience_config.py::test_per_app_fairness`<br>`test_resilience_config.py::test_guarded_sink_opens_and_half_opens` |  |
| INV-52-C055 | Missing | BLOCKED | `docs/RELIABILITY.md` |  | failover execution needs INV-53/INV-54 multi-broker environment |
| INV-52-C056 | Partial | EVIDENCED_LOCAL | `lifecycle.py`<br>`resilience.py` | `test_resilience_config.py::test_security_dependency_outage_fails_closed_noncritical_degrades`<br>`test_resilience_config.py::test_guarded_sink_opens_and_half_opens` |  |
| INV-52-C057 | Partial | EVIDENCED_LOCAL | `adapters.py`<br>`config.py`<br>`docs/RELIABILITY.md` | `test_integration.py::test_offline_queue_reconnect_in_order_no_loss_no_dup`<br>`test_integration.py::test_recovery_objective_under_random_faults` | waiver W-003 |
| INV-52-C058 | Missing | EVIDENCED_LOCAL | `resilience.py` | `test_resilience_config.py::test_fencing_refuses_stale_owner` |  |
| INV-52-C059 | Partial | EVIDENCED_LOCAL | `runtime.py`<br>`lifecycle.py` | `test_runtime_ext.py::test_quarantine_holds_in_dead_letter_not_delivered`<br>`test_runtime_ext.py::test_freeze_is_retryable_disable_is_terminal`<br>`test_resilience_config.py::test_bootstrap_to_ready_and_emergency_disable` |  |
| INV-52-C060 | Missing | EVIDENCED_LOCAL | `tests/test_integration.py` | `test_integration.py::test_recovery_objective_under_random_faults`<br>`test_integration.py::test_sidecar_down_is_retryable_unavailable` |  |
| INV-52-C061 | Missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json`<br>`docs/PERFORMANCE.md` |  |  |
| INV-52-C062 | Partial | DOCUMENTED | `perf/baseline.json`<br>`docs/PERFORMANCE.md` |  |  |
| INV-52-C063 | Missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json` |  |  |
| INV-52-C064 | Missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json` |  |  |
| INV-52-C065 | Missing | EVIDENCED_LOCAL | `bench.py`<br>`docs/PERFORMANCE.md` |  |  |
| INV-52-C066 | Missing | EVIDENCED_LOCAL | `runtime.py`<br>`bench.py`<br>`docs/PERFORMANCE.md` | `test_runtime_ext.py::test_frozen_view_prevents_predicate_mutation` |  |
| INV-52-C067 | Partial | EVIDENCED_LOCAL | `runtime.py`<br>`docs/INTERFACES.md` | `test_runtime_ext.py::test_topic_limit`<br>`test_runtime_ext.py::test_decision_log_bounded`<br>`test_runtime_ext.py::test_window_is_bounded`<br>`test_adversarial.py::test_publish_random_messages_keeps_invariants` |  |
| INV-52-C068 | Missing | BLOCKED | `bench.py` |  | no instrumented edge node; waiver W-002<br>waiver W-002 |
| INV-52-C069 | Partial | DOCUMENTED | `docs/PERFORMANCE.md`<br>`observability.py` | `test_runtime_ext.py::test_health_degrades_on_backlog_and_stall` |  |
| INV-52-C070 | Missing | EVIDENCED_LOCAL | `gate.py`<br>`bench.py`<br>`perf/baseline.json` |  |  |
| INV-52-C071 | Partial | EVIDENCED_LOCAL | `runtime.py`<br>`lifecycle.py`<br>`schemas/PK_MSG_HEALTH_1.schema.json` | `test_governance.py::test_decisions_and_health_match_schema`<br>`test_resilience_config.py::test_bootstrap_to_ready_and_emergency_disable` |  |
| INV-52-C072 | Partial | EVIDENCED_LOCAL | `runtime.py`<br>`observability.py` | `test_runtime_ext.py::test_latency_histogram_and_outcomes`<br>`test_integration.py::test_prometheus_labels_are_bounded` |  |
| INV-52-C073 | Missing | EVIDENCED_LOCAL | `observability.py` | `test_integration.py::test_logs_carry_stable_ids_release_and_no_payload` |  |
| INV-52-C074 | Missing | EVIDENCED_LOCAL | `runtime.py`<br>`adapters.py`<br>`observability.py` | `test_runtime_ext.py::test_traceparent_propagates_to_subscriber_and_decision`<br>`test_integration.py::test_publish_structured_cloudevent`<br>`test_integration.py::test_trace_helpers` |  |
| INV-52-C075 | Partial | EVIDENCED_LOCAL | `observability.py`<br>`docs/OBSERVABILITY.md` | `test_integration.py::test_prometheus_labels_are_bounded`<br>`test_adversarial.py::test_error_details_do_not_echo_payload` |  |
| INV-52-C076 | Partial | EVIDENCED_LOCAL | `runtime.py` | `test_runtime_ext.py::test_every_route_has_a_reason`<br>`test_runtime_ext.py::test_rejections_are_recorded` |  |
| INV-52-C077 | Missing | EVIDENCED_LOCAL | `runtime.py` | `test_runtime_ext.py::test_every_route_has_a_reason` |  |
| INV-52-C078 | Missing | BLOCKED | `observability.py` | `test_integration.py::test_logs_carry_stable_ids_release_and_no_payload` | live infrastructure graph service not available |
| INV-52-C079 | Missing | DOCUMENTED | `observability.py`<br>`docs/OBSERVABILITY.md` | `test_integration.py::test_sampling_never_drops_failures_or_policy` |  |
| INV-52-C080 | Missing | BLOCKED | `deploy/observability/dashboard.json`<br>`deploy/observability/alerts.yaml`<br>`observability.py` | `test_integration.py::test_classifier_distinguishes_classes` | not loaded into a live Prometheus/Grafana |
| INV-52-C082 | Partial | EVIDENCED_LOCAL | `tests/test_runtime_ext.py`<br>`tests/test_governance.py` | `test_integration.py::test_fixture_suite`<br>`test_governance.py::test_publish_request_and_envelope_schema`<br>`test_governance.py::test_every_error_code_is_documented` |  |
| INV-52-C083 | Missing | BLOCKED | `tests/test_integration.py` | `test_integration.py::test_publish_structured_cloudevent` | no live daprd/broker/tier environment |
| INV-52-C084 | Missing | BLOCKED | `.github/workflows/ci.yml`<br>`docs/COMPATIBILITY.md` |  | CI matrix defined but not executed; one platform measured here |
| INV-52-C085 | Missing | EVIDENCED_LOCAL | `tests/test_adversarial.py` | `test_adversarial.py::test_parse_publish_request_bytes`<br>`test_adversarial.py::test_validate_envelope_only_raises_structured_errors`<br>`test_adversarial.py::test_from_cloudevent`<br>`test_adversarial.py::test_config_validate_never_raises`<br>`test_adversarial.py::test_token_verify_fuzz` |  |
| INV-52-C087 | Partial | EVIDENCED_LOCAL | `governance/threats.json` | `test_governance.py::test_threat_map_tests_exist` |  |
| INV-52-C088 | Missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json` |  |  |
| INV-52-C089 | Missing | BLOCKED | `tests/test_integration.py` | `test_integration.py::test_recovery_objective_under_random_faults`<br>`test_integration.py::test_expiry_bounds_offline_age` | disaster / real partition / degraded control-plane tests need infrastructure |
| INV-52-C090 | Missing | EVIDENCED_LOCAL | `gate.py`<br>`evidence/release_certification.json`<br>`tools/sbom.py`<br>`tools/cleanroom.py` | `test_governance.py::test_gate_governance_blocks_and_refuses_self_approval` |  |
| INV-52-C091 | Partial | DOCUMENTED | `docs/SUPPORT_POLICY.md` |  |  |
| INV-52-C092 | Partial | DOCUMENTED | `docs/OPERATIONS.md`<br>`lifecycle.py` | `test_resilience_config.py::test_bootstrap_to_ready_and_emergency_disable` |  |
| INV-52-C093 | Missing | DOCUMENTED | `docs/COMPATIBILITY.md` |  |  |
| INV-52-C094 | Missing | DOCUMENTED | `docs/SUPPORT_POLICY.md` |  |  |
| INV-52-C095 | Partial | DOCUMENTED | `docs/OPERATIONS.md` |  |  |
| INV-52-C096 | Partial | DOCUMENTED | `docs/OPERATIONS.md` |  |  |
| INV-52-C097 | Missing | DOCUMENTED | `docs/OPERATIONS.md`<br>`governance/owners.json` |  |  |
| INV-52-C098 | Missing | DOCUMENTED | `governance/reviews.md` |  |  |
| INV-52-C099 | Missing | EVIDENCED_LOCAL | `governance/waivers.json` | `test_governance.py::test_waivers_have_owner_risk_expiry` | waiver W-004<br>waiver W-005 |
| INV-52-C100 | Missing | BLOCKED | `gate.py`<br>`evidence/release_certification.json` | `test_governance.py::test_gate_governance_blocks_and_refuses_self_approval`<br>`test_governance.py::test_nothing_claims_implemented_without_approval` | gate executes and reports NO_GO: owners, approvals, blocked items |
