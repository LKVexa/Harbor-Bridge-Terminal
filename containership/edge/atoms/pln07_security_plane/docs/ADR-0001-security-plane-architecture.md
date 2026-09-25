# ADR-0001 — PLN-07 security-plane architecture (4.3.0)

**Status:** Proposed — awaiting architecture-review approval (MC-59, external blocker)
**Deciders:** David Paul Russell (owner); security lead (to be named, MC-58)
**Date:** 2026-09-23

## Context
4.2.0 shipped correct grant primitives with no trust path: no identity, policy, signing, time, durable revocation, service boundary or telemetry. `MASTER.md` is not recoverable from the archive (MC-01), so this ADR records decisions against `contract.py`, `CHECKLIST.json` and `SECURITY.md` and lists deltas in `MASTER_DELTA.md`.

## Decisions
1. **Composition, not ownership.** PLN-07 owns the grant model, the boundary contract and the fail-closed composition. Identity (GAP-06), policy (GAP-13), key custody (GAP-07) and site autonomy (GAP-04) plug in through protocols: `identity.Authenticator`, `policy.PolicyEngine`, `signing.KeyStore` backend, `Verifier.revocation_source`. Each ships a reference implementation so the plane runs and is testable alone.
2. **Grant body v2.** `PK_GRANT/2` adds `environment/site/workload/audience` (sticky boundaries), `issued_at/not_before/nonce` (issuance instance, replay binding) and `parent_fingerprint`. `PK_GRANT/1` stays byte-identical so 4.x ids and signatures do not change. `Verifier(require_v2=True)` retires v1 after migration.
3. **Full-strength revocation keys.** Revocation records key on the 64-hex SHA-256 fingerprint; the 16-hex legacy id is carried for 4.x verifiers only.
4. **Signatures.** `PK_SIG/1` envelopes bind trust domain, algorithm and key id to the canonical body. Ed25519 by default; HMAC-SHA256 only when policy allows it (single host/test).
5. **Durable revocation.** Append-only, fsync'd, hash-chained JSON-lines log with epoch fencing, idempotent writes, per-site acks, horizon-breach detection and tombstone compaction.
6. **Fail-closed everywhere.** Unknown time, revocation state, policy result, signature, API version or field → deny with a stable `code`.
7. **Stdlib first.** The core has no runtime dependencies; `cryptography` is optional for Ed25519.

## Scoped out (MC-08)
WIT capability plumbing, hardware VM isolation, CHERI/SFI and Spectre mitigations belong to the execution planes (PLN-01/03/04). PLN-07 provides the grant they must check; enforcement evidence comes from their integration tests (MC-07, MC-50).

## Consequences
The plane runs self-contained. Production still depends on the external adapters listed in `evidence/EXTERNAL_BLOCKERS.json`; the gate cannot return GO while any is open.
