# Audit integrity (INV-38-C049)

`audit_log.py` emits an append-only, hash-chained security audit stream. Each
record links the previous record's digest; the offline `verify_chain` detects
deletion, insertion, reordering and mutation. Secrets/payloads are never stored;
control characters are rejected so records cannot be forged by log injection.
Schema: `audit/event.schema.json`. Tests: `tests/test_audit_log.py` (and the
offline verifier fixtures under `audit/verification-tests/`). **Status:** `DONE`.
