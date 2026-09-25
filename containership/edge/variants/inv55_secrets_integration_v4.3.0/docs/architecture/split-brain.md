# Split-brain and distributed duplicate protection

| ID | INV55-ARCH-SPLITBRAIN | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

- The provider is the source of truth for secret versions (`contract.py::build` `source_of_truth`). There is no leader.
- Concurrent rotations: `rotate` passes `expected_version` as Vault KV v2 `options.cas` (`VaultProvider.write`). The losing writer gets HTTP 400 `check-and-set` → `ProviderConflict` → `CONFLICT` (INV55-E019, 409, terminal). Rotators SHOULD always send `expected_version`; without it, last write wins. Evidence: `tests/test_service_contract.py::RotateContract.test_cas_conflict`, `tests/test_vault_adapter.py::VaultHttp.test_write_read_versions_and_cas`.
- KV v1 has no CAS; concurrent rotation on KV v1 is UNSUPPORTED.
- Idempotency is an atomic per-process reservation keyed `tenant/name/key`: the first request performs the write, concurrent duplicates wait and replay its result, the same key with a different value → CONFLICT (audited `idempotency_payload_mismatch`), and a failed attempt releases the key. Evidence: `tests/test_concurrency.py::Races.test_duplicate_rotation_without_cas_writes_once`, `test_same_idempotency_key_different_payload_conflicts`, `test_concurrent_idempotent_rotate_single_version`.
- It is still single-instance: duplicates on different instances both write unless `expected_version` is used. Cross-instance fencing is NOT IMPLEMENTED (traceability #58: PARTIAL).
- Per-instance state that can diverge: leases, cache, and — even with `state_path` — scopes and retirements (each instance has its own state file; no replication). No fencing token, epoch or gossip. NOT IMPLEMENTED. Mitigations: apply scopes to every instance; `retire(destroy=true)`; small `cache_ttl_s`.
- Within one process: `SecretsService._lock` (RLock). Evidence: `tests/test_concurrency.py::Races.test_parallel_resolve_use_rotate_keeps_invariants`, `test_revoke_races_use`.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Atomic idempotency reservation |
| 4.3.0 | 2026-09-22 | CONFLICT code; idempotency scope; tests |
