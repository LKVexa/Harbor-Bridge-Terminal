# Threat model and adversarial coverage (M23)

Assets: call integrity, argument confidentiality, tenant isolation, callee availability,
audit integrity. Adversaries: network MITM, unenrolled host, enrolled-but-malicious peer,
resource exhauster, insider editing logs.

| ID | Threat | Control | Test (all run in this build) | Residual |
|---|---|---|---|---|
| T-01 | Argument misread after signature drift | fingerprint before decode | `test_signature_drift_rejected_before_args_decoded` | 64-bit fp is a drift detector, not a MAC (auth is the record layer) |
| T-02 | Version downgrade by MITM | offered list in MAC'd transcript | `test_downgrade_by_mitm_is_detected` | — |
| T-03 | Unenrolled / expired / revoked peer | keyring lookup, one error code | `test_unknown_expired_revoked_and_wrong_peer_share_one_code`, `test_unknown_peer_and_unenrolled_peer` | — |
| T-04 | Record replay / reorder / reflection | per-session seq window + direction nonce | `test_replayed_record_rejected`, `test_reflection_rejected`, `test_record_replay_on_live_session_kills_session` | cross-session re-send of a request id is *answered from the idempotency cache*, not rejected; `ReplayWindow.check_request` exists but the node does not use it |
| T-05 | Ciphertext tamper, forged record | AES-GCM, window advances only after auth | `test_tampered_ciphertext_and_seq_rejected`, `test_forgery_does_not_advance_window` | — |
| T-06 | Cross-tenant call | tenant bound to authenticated peer, never client-chosen; exact tenant match | `test_no_cross_tenant_glob_and_expiry_and_revoke`, `test_authorization_default_deny_and_tenant_isolation` | — |
| T-07 | Memory exhaustion via length claims | size refused before allocation; element count bounded by remaining bytes | `test_oversize_length_prefix_refused_without_allocation`, `test_hostile_length_prefix_does_not_allocate` | — |
| T-08 | Slowloris / connection flood | handshake timeout, idle timeout, connection cap | `test_slowloris_handshake_times_out`, `test_connection_limit` | per-IP limits not implemented |
| T-09 | Callee overload | admission + per-tenant cap + typed shed | `test_overload_sheds_with_typed_error` | — |
| T-10 | Audit log tampering | hash chain + fsync + external head | `test_audit_chain_detects_edit_delete_reorder_truncate` | head must be stored off-host by operations |
| T-11 | PSK compromise | rotation, revocation (ends live sessions) | `test_rotation_overlap_then_old_key_expires`, `test_revoked_key_ends_live_session` | **no forward secrecy** — open |
| T-12 | No PKI / cert identity | — | — | **open**: mTLS substitution per ADR-0001 |
| T-13 | Secrets in logs/traces | key-based redaction; span attrs capped at 16 | `test_logger_redacts_truncates_filters_ratelimits`, `test_traceparent` | trace attribute *values* are not length-bounded or pattern-redacted — open |
| T-15 | Audit flood by unauthenticated handshakes | deny records rate-limited to 20/s, remainder counted | — (no dedicated test) | open |
| T-16 | Caller forces 100 % trace sampling | none: parent `sampled` flag is honoured per W3C | `test_traceparent` asserts the current behaviour | decision needed (TELEMETRY_POLICY.md) |
| T-14 | Parser crash on hostile bytes | bounded decoder, fuzzing | `test_mutation_fuzz_only_raises_codec_error`, `test_header_fuzz` | campaign is seconds, not hours (M24) |

Secure-implementation review by an independent reviewer: **not performed** (no reviewer
available to this build). Status OPEN.
