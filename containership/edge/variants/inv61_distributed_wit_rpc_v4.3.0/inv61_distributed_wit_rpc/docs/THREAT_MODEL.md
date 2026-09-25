# INV-61 Threat Model (STRIDE) — 4.3.0

Assets: correct argument interpretation; callee integrity; tenant isolation; availability; audit integrity; key material.
Actors: external network attacker; malicious tenant with valid credentials; compromised peer node; insider with log access.

| ID | STRIDE | Threat | Control | Abuse-case test |
|---|---|---|---|---|
| T01 | S | Forged sender / spoofed principal | HMAC envelope bound to key principal; TLS CN binding | `test_spoofed_sender`, `test_tls_peer_binding`, `test_mutual_tls_and_identity_binding` |
| T02 | T | Payload tampering in transit | TLS 1.3 + envelope MAC | `test_tampered_payload_rejected` |
| T03 | R | Denial of having made a call | Audit chain + request IDs | `test_chain_detects_tampering` |
| T04 | I | Callee exception details leak | Typed `callee-trap`, no detail | `test_ac06_callee_trap_no_leak` |
| T05 | I | Secrets in logs | Mandatory redaction, key `repr` scrubbed | `test_ac12_secrets_not_logged`, `test_logger_schema_and_redaction` |
| T06 | D | Oversize length prefix / memory exhaustion | Header check before alloc; string/collection/depth caps | `test_header_checked_before_allocation`, `test_decode_rejections`, `test_ac13_oversize_string_arg` |
| T07 | D | Connection flood / slowloris | Connection cap, accept rate bucket, handshake + idle timeouts | `test_connection_cap_and_handshake_timeout`, `test_truncated_and_slowloris_frames` |
| T08 | D | Request flood by one tenant | Per-tenant in-flight + token bucket; global ceiling | `test_overload_is_shed_with_retryable_status`, `test_admission` |
| T09 | E | Calling functions not granted | Default-deny policy, explicit deny wins | `test_default_deny_and_explicit_deny` |
| T10 | S/T | Replay of captured frame | Nonce + skew window + bounded cache | `test_replay_and_window`, `test_bounded_cache_fails_closed` |
| T11 | T | Version downgrade | Transcript MAC | `test_downgrade_detected`, `test_version_negotiation_down_to_2_0` |
| T12 | T | Signature drift misread | Fingerprint check before arg decode | `test_ac01_signature_drift`, `test_ac03_type_confusion_args` |
| T13 | T | Split-brain duplicate mutation | Leases + fencing epochs | `test_lease_no_split_brain_and_fencing`, `test_ac09_unowned_mutation_fenced` |
| T14 | T | Duplicate execution via retry | Idempotency keys; non-keyed calls never retried | `test_ac11_duplicate_execution_suppressed`, `test_idempotent_duplicates_race_to_single_execution` |
| T15 | T | Audit log edit/delete/truncate | HMAC chain, anchored head in checkpoint | `test_chain_detects_tampering` |
| T16 | E | Parser crash / unexpected exception | Only `CodecError` escapes decoder; fuzzed | `test_mutation_fuzz_never_raises_unexpected` |
| T17 | D | Metric cardinality explosion | Series cap → `__overflow__` | `test_metrics_render_and_cardinality_cap` |
| T18 | I | Cross-tenant data via telemetry | Tenant class labels only; span attr allow-list | `test_traceparent` |

## Residual risks (tracked in WAIVERS.md)

* Side channels (timing of authz decisions) are not tested — W-008.
* Python threads cannot be forcibly killed: a callee that ignores its cancellation token keeps running after `deadline-exceeded` is returned (it cannot affect the response) — W-009.
* Responses are protected by TLS only (no response MAC); plaintext mode is for tests — enforced off in production by `require_tls` (config immutable key).
* The 64-bit fingerprint is a drift detector, not a security control.
