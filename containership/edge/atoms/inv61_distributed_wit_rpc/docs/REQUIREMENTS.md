# INV-61 v4.3.0 — Normative requirements and traceability (M21)

Keywords MUST / SHOULD / MAY per RFC 2119. Every requirement names the code that
implements it and the test that proves it; `tools/checklist_status.py --check`
fails if a named test id stops existing.

| ID | Requirement | Code | Test |
|---|---|---|---|
| R-FRAME-01 | A frame MUST name interface, version and function and carry a 64-bit signature fingerprint. | `wrpc/codec.py::encode_frame` | `test_wit_codec.CodecTest.test_envelope_header_decoded_without_touching_args` |
| R-FRAME-02 | The receiver MUST compare the fingerprint before decoding any argument byte. | `wrpc/node.py::Node.handle` | `test_node_e2e.EndToEndTest.test_signature_drift_rejected_before_args_decoded` |
| R-FRAME-03 | Exact version match is REQUIRED; a mismatch MUST return `version-mismatch` with the expected version. | `Node.handle` | `test_node_e2e.EndToEndTest.test_version_drift_rejected` |
| R-DEADLINE-01 | A call at or past its absolute deadline MUST NOT dispatch. | `Node.handle`, `rpc.Endpoint.handle` | `test_node_e2e.AdversarialTest.test_expired_deadline_never_dispatches` |
| R-DEADLINE-02 | The deadline MUST be re-checked after admission queueing, before any side effect. A callee finishing after its deadline MUST return `deadline-exceeded` with `executed: true`, so the caller knows the side effect happened; callers MUST use request ids. | `Node._execute` | `test_node_e2e.EndToEndTest.test_typed_errors_not_transport_failures` |
| R-ERR-01 | Failures MUST be typed errors (`PK_WRPC_ERROR/1`), never a dropped session, except record-layer security failures, which MUST end the session. | `node._err` | `test_node_e2e.EndToEndTest.test_typed_errors_not_transport_failures`, `AdversarialTest.test_record_replay_on_live_session_kills_session` |
| R-CODEC-01 | Encoding MUST be canonical: `encode(decode(b)) == b` for every accepted `b`. | `wrpc/codec.py` | `test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error` |
| R-CODEC-02 | Decoding MUST be bounded (1 MiB frame, 65 536 elements, depth 32) and raise only `CodecError`. | `wrpc/codec.py::Reader` | `test_wit_codec.PropertyAndFuzzTest.test_hostile_length_prefix_does_not_allocate`, `test_wit_codec.PropertyAndFuzzTest.test_nesting_depth_limit_enforced`, `test_wit_codec.PropertyAndFuzzTest.test_list_of_zero_size_elements_round_trips` |
| R-CODEC-03 | Byte layouts MUST match the hand-derived golden vectors. | `wrpc/codec.py` | `test_wit_codec.CodecTest.test_golden_vectors` |
| R-WIT-01 | Unsupported WIT constructs MUST be rejected with a stable code, never ignored. | `wrpc/wit.py` | `test_wit_codec.WitParserTest.test_rejections_are_stable` |
| R-NEG-01 | The most-preferred common version MUST be chosen; no common version MUST fail. | `security.negotiate` | `test_security.NegotiationTest.test_highest_common`, `test_security.NegotiationTest.test_no_common` |
| R-NEG-02 | A downgrade by version stripping MUST be detected. | `ClientHandshake.finish` | `test_security.NegotiationTest.test_downgrade_by_mitm_is_detected` |
| R-AUTHN-01 | Peers MUST mutually authenticate before any frame; all credential failures MUST share one code. | `security.py` | `test_security.HandshakeTest.test_mutual_auth_and_channel`, `test_security.HandshakeTest.test_wrong_psk_fails_both_directions`, `test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code` |
| R-AUTHN-02 | Credentials MUST support expiry, rotation with overlap, and revocation. | `security.Keyring` | `test_security.HandshakeTest.test_rotation_overlap_then_old_key_expires` |
| R-AUTHZ-01 | Calls MUST be default-deny; explicit deny beats allow; grants never cross tenants; every decision is audited. | `controls.Authorizer`, `Node.handle` | `test_controls_ops.AuthorizerTest.test_default_deny_grant_and_deny_precedence`, `test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation` |
| R-ENC-01 | Records MUST be AEAD-protected with a never-repeating nonce and direction binding. | `security.Channel` | `test_security.ChannelTest.test_tampered_ciphertext_and_seq_rejected`, `test_security.ChannelTest.test_reflection_rejected`, `test_security.ChannelTest.test_nonce_never_repeats` |
| R-REPLAY-01 | A replayed or reordered record MUST be rejected and end the session; a forgery MUST NOT advance the window. | `Channel.open` | `test_security.ChannelTest.test_forgery_does_not_advance_window` |
| R-IDEM-01 | A duplicate request id within TTL MUST return the first *final* outcome without re-execution, including across reconnects and restarts (with a journal). Transient refusals MUST NOT be remembered. Reusing an id for a different call MUST return `idempotency-conflict`. | `controls.IdempotencyCache`, `ops.Journal` | `test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay`, `test_node_e2e.DefectRegressionTest.test_retry_after_overload_eventually_executes`, `test_node_e2e.DefectRegressionTest.test_request_id_reuse_across_functions_conflicts` |
| R-RETRY-01 | Only idempotent calls with retryable errors MAY be retried, within deadline and a retry budget. | `controls.RetryPolicy` | `test_controls_ops.IdempotencyRetryTest.test_retry_only_idempotent_retryable_and_within_deadline`, `test_controls_ops.IdempotencyRetryTest.test_retry_budget_caps_amplification`, `test_controls_ops.IdempotencyRetryTest.test_retry_honours_retry_after_hint` |
| R-ADMIT-01 | Concurrency MUST be bounded globally and per tenant; overload MUST return `overloaded` with `retry_after_ms`. | `controls.Admission` | `test_node_e2e.FaultInjectionTest.test_overload_sheds_with_typed_error` |
| R-BREAK-01 | A client circuit breaker MUST open after consecutive failures and admit a single half-open probe. | `controls.CircuitBreaker` | `test_controls_ops.AdmissionBreakerLeaseTest.test_breaker_state_machine` |
| R-FENCE-01 | A stale fencing token MUST NOT be able to write after failover. | `controls.LeaseTable` | `test_controls_ops.AdmissionBreakerLeaseTest.test_fencing_prevents_duplicate_owner_writes` |
| R-CONF-01 | Config MUST be validated before activation, carry a provenance digest, roll back atomically, and never contain secret values. | `ops.ConfigStore` | `test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback` |
| R-AUDIT-01 | Security events MUST be hash-chained and fsync'd; verification MUST detect edit, delete, reorder and (with an external head) truncation. | `ops.AuditLog` | `test_controls_ops.OpsTest.test_audit_chain_detects_edit_delete_reorder_truncate` |
| R-OBS-01 | Metrics MUST use an allow-listed label set with a series cap; logs MUST redact secrets and arguments; traces MUST follow W3C traceparent. | `ops.Metrics/JsonLogger/Tracer` | `test_controls_ops.OpsTest.test_metrics_exposition_and_cardinality_cap`, `test_controls_ops.OpsTest.test_logger_redacts_truncates_filters_ratelimits`, `test_controls_ops.OpsTest.test_traceparent` |
| R-HEALTH-01 | Readiness MUST fail when a critical dependency fails or the node is draining. | `ops.Health` | `test_controls_ops.OpsTest.test_health_readiness` |
| R-CONC-01 | Shared counters and caches MUST keep exact totals under concurrent use. | `rpc.Endpoint._count`, locks throughout | `test_controls_ops.ConcurrencyTest.test_endpoint_stats_exact_under_threads`, `test_controls_ops.ConcurrencyTest.test_metrics_and_audit_under_threads` |
| R-LIFE-01 | Stopping a node MUST tear down live sessions. Draining MUST fail readiness, refuse new connections, answer new calls `unavailable`, and wait for in-flight calls. | `Node.stop`, `Node.drain` | `test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay`, `test_node_e2e.DefectRegressionTest.test_drain_refuses_new_work_and_readiness_fails` |
| R-AUTHN-03 | Revoking or expiring a credential MUST end sessions established with it at their next record. | `Node._serve` | `test_node_e2e.DefectRegressionTest.test_revoked_key_ends_live_session` |
| R-AUDIT-02 | If an authorization decision cannot be audited the call MUST fail closed (`unavailable`) and readiness MUST fail. | `Node._audit` | `test_node_e2e.DefectRegressionTest.test_audit_failure_fails_closed_and_flips_readiness` |
| R-DEP-01 | A missing `pk_core` MUST fail with a named requirement, not skip silently, in the release job. | `wrpc/pkcore_compat.py` | `test_pk_core_compat.PkCoreProbeTest.test_missing_symbol_detected`, `test_pk_core_compat.PkCoreProbeTest.test_release_gate_requires_pk_core` |

## Failure taxonomy (PK_WRPC_ERROR/1)

`malformed-frame`(+code) · `deadline-exceeded` · `unknown-interface` · `version-mismatch`(+expected) ·
`unknown-function` · `signature-mismatch` · `permission-denied` · `overloaded`(+retry_after_ms) ·
`malformed-args`(+code) · `unimplemented` · `callee-trap` · `result-type`(+code) · `idempotency-conflict` · `unavailable`(+retry_after_ms) — caller-side only:
`transport` · `circuit-open` · `malformed-response`. Retryable: `overloaded`, `transport`, `circuit-open`, `unavailable`.

## Precedence of checks

size → record authentication → replay → credential still valid → header decode → draining → deadline → interface → version →
function → fingerprint → authorization → idempotency → admission → argument decode → dispatch.
An earlier failure always wins, so a caller learns nothing about authorization from a frame
that fails an earlier check.
