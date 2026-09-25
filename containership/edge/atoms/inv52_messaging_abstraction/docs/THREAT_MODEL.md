# Threat model — `DOC-INV52-TM` v4.3.0 (C041, C087)

Status: PROPOSED. Written by the build from the interface inventory; it is **not** an independent security review (C041 stays open until one is recorded).

Actors: malicious tenant, compromised workload/subscriber, hostile operator config change, network attacker, compromised node/provider. Machine-readable map: `governance/threats.json` (checked by `test_governance.py`).

| ID | STRIDE | Threat | Control | Tests |
|---|---|---|---|---|
| T01 | S | Spoofed publisher identity (source field forged) | TenantBus token identity; source==app check | `test_security.py::test_source_must_match_token_identity`<br>`test_runtime.py::test_authorization_and_source_spoofing` |
| T02 | E | Publishing to a topic the app does not own | fail-closed allow-list; explicit capabilities | `test_security.py::test_least_privilege_nothing_by_default_and_revocation` |
| T03 | I | Malicious tenant reads/writes another tenant's topic or dead letters | tenant-namespaced topics; separator injection refused | `test_security.py::test_tenants_cannot_cross`<br>`test_security.py::test_dead_letters_are_tenant_scoped` |
| T04 | S | Token forgery, expiry abuse, replay | HMAC-SHA256, TTL<=3600, nonce cache, fail closed when cache full | `test_security.py::test_forged_expired_replayed_malformed_tokens_denied`<br>`test_adversarial.py::test_replay_of_captured_token_and_cross_tenant_token` |
| T05 | E | Identity/key/time service outage used to bypass checks | deny on provider/clock failure; security dependency blocks publish | `test_security.py::test_key_provider_or_clock_outage_denies`<br>`test_resilience_config.py::LifecycleTest::test_security_dependency_outage_fails_closed_noncritical_degrades` |
| T06 | R | Message silently dropped | dead-letter every zero-delivery message with reason; bounded & counted eviction | `test_runtime.py::test_dead_letter_reasons_for_no_route_and_handler_failure`<br>`test_runtime.py::test_dead_letter_is_bounded` |
| T07 | T | Compromised subscriber mutates another subscriber's view / policy | deep copies; read-only predicate view | `test_adversarial.py::test_predicate_cannot_escalate_by_mutating_policy_through_message`<br>`test_runtime_ext.py::CompatTest::test_frozen_view_prevents_predicate_mutation` |
| T08 | D | Resource exhaustion (huge/deep payload, route/topic flood, publish flood) | size/depth/route/topic limits; token-bucket admission; bounded tables | `test_adversarial.py::test_json_nesting_bomb_rejected_without_recursion_error`<br>`test_resilience_config.py::AdmissionTest::test_per_app_fairness` |
| T09 | D | Parser crash on untrusted bytes | size before parse; structured errors only | `test_adversarial.py::FuzzTest::test_parse_publish_request_bytes`<br>`test_adversarial.py::FuzzTest::test_validate_envelope_only_raises_structured_errors` |
| T10 | I | Secrets leaked via config, logs, audit or error details | config secret rejection; redaction; payload never logged; exception text never copied | `test_security.py::test_audit_redacts_secrets`<br>`test_adversarial.py::test_error_details_do_not_echo_payload` |
| T11 | T | Tampering with or truncating the audit trail | SHA-256 hash chain with externally recorded head | `test_security.py::test_tamper_reorder_and_truncation_detected` |
| T12 | T | Unapproved or tampered adapter artifact | digest allow-list with provenance | `test_security.py::test_artifact_admission` |
| T13 | T | Stale controller / split brain double-owns a subscription | fencing tokens with leases | `test_resilience_config.py::BreakerFencingTest::test_fencing_refuses_stale_owner` |
| T14 | I | Cross-tenant telemetry leak / high-cardinality label abuse | fixed label set; tenant field only from namespace | `test_integration.py::ObservabilityTest::test_prometheus_labels_are_bounded`<br>`test_integration.py::ObservabilityTest::test_logs_carry_stable_ids_release_and_no_payload` |
| T15 | T | Log injection via topic names | JSON-encoded structured logs; length limits | `test_adversarial.py::test_log_injection_in_topic_names_is_contained` |
| T16 | E | Hostile config change (wildcard publishers, secret, bad limits) | validation before activation; author provenance; rollback | `test_resilience_config.py::ConfigTest::test_validation_catches_every_class`<br>`test_resilience_config.py::ConfigTest::test_activation_is_atomic_and_invalid_keeps_previous` |
| T17 | I | Transport eavesdropping / MITM between app, sidecar and broker | EXTERNAL: Dapr Sentry mTLS, broker TLS (deploy/dapr enableTLS) | external — no local test |
| T18 | E | Hostile node / host compromise, side channels | EXTERNAL: platform isolation (INV-40/INV-45 series); out of scope of a library | external — no local test |

## Residual risks

* T17/T18 are enforced outside this package; evidence must come from the Dapr/platform owners.
* `TokenAuthority` is a symmetric-key scheme: any holder of the key can mint tokens; production SHOULD use the platform IdP (SPIFFE/OIDC) and treat this as the local reference.
* The replay cache is per process; multi-replica replay protection needs a shared nonce store (INV-53) or short TTLs.
