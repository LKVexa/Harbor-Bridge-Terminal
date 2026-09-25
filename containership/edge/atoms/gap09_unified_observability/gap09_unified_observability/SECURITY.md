# Security Notes - GAP-09 v5.0.0

## Trust boundary

`SignalStore.submit_verified` is the production entry point. It does not trust attestation level, tenant authorization or signature validity supplied directly by the caller. A configured `TrustVerifier` must validate external trust evidence and return a `ReporterAuthority`; the store then enforces that authority against every sample.

The adapter is expected to integrate with GAP-06 (device identity/attestation) and GAP-07 (signature/provenance). `HMACFixtureVerifier` exists only for deterministic tests.

## Fail-closed rules

The store refuses missing ingest verifiers, invalid signatures, unknown reporters, expired/unsupported authority, over-scoped samples, replayed submission IDs, empty/oversized batches, malformed identifiers, out-of-domain timestamps, non-finite/out-of-range values, query-time regressions, cross-tenant reads and equal-timestamp conflicts.

## Known limitations

The replay cache is bounded and in-memory, so replay defense is not durable across process restart and old replay IDs are eventually evicted. There is no production key-rotation implementation, mTLS transport, persistent tamper-evident audit ledger, distributed authorization policy service, authenticated query-principal adapter, or time-authority integration in this archive. `SignalStore.read()` is therefore an in-process reference boundary: its `caller_tenant` argument must be supplied by trusted application code derived from an authenticated principal, never copied from an untrusted network request. These gaps are tracked in `MISSING_COMPONENTS.md`.
