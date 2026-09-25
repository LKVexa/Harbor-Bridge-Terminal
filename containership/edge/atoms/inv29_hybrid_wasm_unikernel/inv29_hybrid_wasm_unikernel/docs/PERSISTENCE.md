# Persistence, idempotency and lifecycle (INV29-MC059, MC060, MC061)

## Store contract (`lifecycle.Store`)
* Key: composition id = `sha256(canonical({tenant, module, host, module_digest, host_digest, imports, nonce}))`.
* Value: canonical JSON with an embedded `_digest`; every read re-checks it (`StoreCorrupt` on mismatch).
* Writes are atomic (temp + fsync + rename). Ids are validated as 64-hex, so path traversal is impossible.
* The reference backend is a local directory. Any replacement must keep: atomic single-document writes, read-your-writes, integrity check on read, and backup/restore with a manifest digest.

## Idempotency (`Lifecycle.submit`)
The same logical request (same id) returns the stored outcome — admitted *or* refused — without re-running admission. This is what makes client retries safe even though the replay guard would refuse a second admission of the same nonce. Proven under a 32-way race in `test_concurrency::test_idempotent_submit_under_race`.

## State machine
```
PENDING ──► ADMITTED ──► RUNNING ──► RETIRED
   │            │  │         │
   ▼            │  └──► EXPIRED (TTL elapsed before start)
REFUSED         └────► REVOKED ◄──┘ (key revoked, tenant de-authorised, disable, record no longer verifies)
```
Terminal: REFUSED, REVOKED, EXPIRED, RETIRED. Illegal transitions raise `IllegalTransition` (`INV29-E-LIFECYCLE`). History is appended on every transition.

## Reconciliation
`Lifecycle.reconcile()` re-verifies every live composition against current keys, policy, disable state and time. It is idempotent and safe to run on a timer (recommended: every 60 s, and immediately after any key revocation or policy change).

## Backup / restore / reconstruction (MC066)
`Store.backup(path)` writes one self-verifying file; `restore` refuses a tampered backup. After restore, run `reconcile()` — it re-derives every verdict from current trust state, so a restored store can never resurrect a revoked composition. Exercised in `test_lifecycle::test_backup_restore_disaster_recovery`.
