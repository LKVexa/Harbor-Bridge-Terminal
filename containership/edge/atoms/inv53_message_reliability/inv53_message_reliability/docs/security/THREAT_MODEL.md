# INV-53 threat model (C041) — STRIDE over the broker boundary

Assets: message payloads (tenant data), lease tokens (settlement authority), the journal/snapshot (durable
truth), keys, the audit log, configuration. Trust boundaries: client ↔ broker (wire), broker ↔ storage,
broker ↔ key provider, broker ↔ audit/telemetry sink, operator ↔ admin functions.

| Id | Threat (STRIDE) | Control | Test |
|---|---|---|---|
| T1 | Spoofed producer/consumer (S) | HMAC-SHA256 request signing, principal bound to key id | `test_service.py::BrokerTest::test_T1_unauthenticated_is_refused_and_audited`, `test_security.py::AuthnTest::*` |
| T2 | Cross-tenant read/settle (I, E) | Tenant-scoped grants, per-tenant storage directories, default deny | `test_T2_cross_tenant_access_denied_even_with_same_queue_name` |
| T3 | Request replay (S, T) | Nonce cache within skew window; saturation fails closed | `test_T3_replayed_request_refused`, nonce saturation test |
| T4 | Stale consumer settles newer delivery (T) | Lease fencing tokens | `test_T4_stale_consumer_cannot_settle_redelivered_message` |
| T5 | Path traversal via tenant/queue names (T, E) | Name validation (no `/`, printable, trimmed) | `test_T5_path_traversal_names_refused` |
| T6 | Resource exhaustion (D) | Size/depth/in-flight/queue-count limits, quotas, shedding | `test_T6_oversized_and_malformed_inputs`, quota/shedding tests |
| T7 | Audit suppression (R) | Audit failure fails the request closed; chain + external anchor | `test_T7_audit_sink_outage_fails_closed`, audit tail-truncation test |
| T8 | Data leakage via logs/metrics (I) | Redaction by field name, label allow-list, no payload in audit | `test_T8_logs_and_metrics_never_contain_payload_or_lease` |
| T9 | Journal tampering (T) | Hash-chained journal; snapshot digest; restore manifest | durable corruption/tamper tests |
| T10 | Split brain on shared storage (T) | OS lock + epoch fencing | `test_epoch_fencing_refuses_superseded_writer` (single host) |
| T11 | Key compromise (S) | Rotation to a new active key, verify-only overlap, retirement | `test_rotation_and_retirement` |
| T12 | Error-message information leak (I) | Internal errors return `E_INTERNAL` with type name only | `test_internal_errors_do_not_leak` |
| T13 | Payload confidentiality at rest (I) | **Not implemented** — see ENCRYPTION.md | BLOCKED |
| T14 | Malicious dependency (T) | Runtime is stdlib-only; pk_core pinned by content digest; SBOM | CI `pk_core` + `reproducible` lanes |
| T16 | Client-chosen time used to expire another consumer's lease (T, E) | Broker clock times leases; wire `now` ignored | `test_R5_client_supplied_time_cannot_steal_a_lease` |
| T17 | Tenant enumeration via health (I) | Wire health filtered to the caller's tenant | `test_R4_health_over_the_wire_shows_only_the_callers_tenant` |
| T18 | Silent loss of the journal tail (T) | Clean-shutdown head marker; optional external anchor | `test_tail_removal_after_clean_shutdown_is_detected`, `test_external_anchor_detects_tail_loss_after_a_crash` |
| T15 | Operator abuse of redrive/purge (R, E) | Separate `redrive` action, audited; purge is offline CLI + service_owner decision right | redrive audit assertion |

Residual risks: no transport encryption (TLS is the transport's job and is not provided here); no
encryption at rest; cross-host fencing depends on a consensus service not in this package; the
threat model has not been reviewed by a named security_owner.
