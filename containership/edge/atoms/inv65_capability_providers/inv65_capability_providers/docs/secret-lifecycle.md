# Secret lifecycle (M09)

1. Link config may hold only `secret_ref` (`secret://…`); inline secret-like keys are rejected (4.2.0 rule kept).
2. At call time the resolver fetches from INV-55 **in the caller's scope**; values are wrapped in `SecretValue` (redacting repr, zeroizable).
3. Cache TTL default 30 s; on rotation INV-55 (or the operator) calls `invalidate(ref)`, which zeroizes cached values. Outage past TTL fails closed — no stale reuse.
4. Every resolution is audited as `secret.use` with the ref, never the value.
5. Values never appear in WAL, snapshots, backups, audit, logs, traces, metrics or error envelopes (asserted in `tests/security/test_secret_handling.py`).

**Production gap:** the INV-55 adapter here is an in-memory fixture; the real INV-55 client must implement `SecretBackend.fetch(ref, scope) -> (bytes, version)`.
