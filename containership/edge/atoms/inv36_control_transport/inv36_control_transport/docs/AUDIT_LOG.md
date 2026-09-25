# Tamper-evident security audit log (MC-18)

Implementation: `audit_log.py`. Event schema: `schema/audit-event.schema.json`.

- **Record**: canonical JSON line with `event_id`, wall `ts` + `mono`, `clock_source`, `node`, `component_version`, `segment`, `actor`, `target`, `tenant`, `decision`, `reason`, `correlation_id`, redacted `data`, `seq`, `prev`, `hash`.
- **Mandatory events** (`MANDATORY_EVENTS`): handshake success/failure, authorization decisions, key rotate/revoke/rollback(+denied), config activate/rollback/validation failure/rollback denied, quarantine request/activate/expire/remove/rejected, break-glass, policy activate/rollback denied, integrity failures, replay thresholds, release sign/certify, kill switch.
- **Redaction**: keys containing secret/key_bytes/private/plaintext/payload/shared/password/token are replaced with `<redacted>`; bytes become `<bytes:N>`; strings capped at 256 chars; at most 32 fields, depth 3. JSON escaping keeps attacker text on one line (no log injection).
- **Integrity**: SHA-256 hash chain over every record; Ed25519-signed checkpoints every 64 records (configurable) binding head, count, segment, component version, node and signing key ID. Segment = process lifetime (new segment ID per start).
- **Append-only**: `O_APPEND` + `fsync` per record, file mode 0600; the component never rewrites or deletes records. Storage-level immutability (WORM bucket / chattr +a) is a deployment requirement.
- **Sink outage**: non-critical events buffer in memory (bounded, drop-oldest, counted - the dropped sequence numbers appear as a detectable chain gap); security-critical events (`SECURITY_CRITICAL`) fail closed with `AuditUnavailable`, so the guarded action does not proceed.
- **Crash**: a torn final line is detected by the verifier (`torn_tail`) and truncated on reopen.
- **Verification**: `verify_log(path, trusted_keys, require_checkpoint, expected_head)` reports the first corruption point: `hash_mismatch`, `chain_break`, `sequence_gap`, `duplicate_event`, `checkpoint_mismatch`, `bad_checkpoint_signature`, `untrusted_checkpoint_key`, `torn_tail`, `head_mismatch_truncation`, `no_checkpoint`; machine-readable `inv36.audit-verify/1`. Ship the chain head + last checkpoint to an external store (telemetry exporter) so local truncation is detectable; run the verifier periodically (CI nightly job and ops cron).
- **Retention / access**: `audit_log.RETENTION_POLICY` (prod 400 days + legal hold); tenants see only their own records; nobody may mutate segments. Transport/storage encryption of audit segments is independent of operational logs (separate sink and key).

Tests: `tests/test_audit_observability.py::AuditLogTest`.
