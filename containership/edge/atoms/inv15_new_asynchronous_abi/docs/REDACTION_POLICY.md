# Handle redaction policy
- Handle tokens MAY exist only in: the host table, the guest's handle object, and authenticated serialized blobs.
- Tokens MUST NOT appear in: logs, events, metrics, audit records, explain output, error details, `repr`/`str`.
- Correlation uses `HMAC-SHA256(host_redaction_key, token)[:16 hex]`; the key is per host process and never exported.
- Enforced by `test_security_telemetry.TestRedaction.test_no_token_anywhere_observable` (full and 8-byte prefix search over every observable surface).
- Crash dumps / core files are NOT covered: a process dump contains the table.
