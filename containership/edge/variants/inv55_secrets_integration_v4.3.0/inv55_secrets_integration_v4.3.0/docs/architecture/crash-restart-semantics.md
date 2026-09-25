# Crash / restart / replay semantics

| ID | INV55-ARCH-CRASH | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| State | Field | Persistence | After restart |
|---|---|---|---|
| Scopes | `_scopes` | Durable when `state_path` set (write-ahead `_save_state`: prospective state → tmp file 0600 → fsync → `os.replace`, then memory is mutated; reloaded by `_load_state`) | Restored. Without `state_path`: lost → every resolve DENIED `out_of_scope` (fail-closed) |
| Retired versions | `_retired` | Same as scopes | Restored. Without `state_path`: lost → a retired-but-not-destroyed version becomes servable again (unsafe) |
| Leases | `_leases`, `_per_subject` | Memory only, by design | Lost; `use` → CONTEXT_MISMATCH; clients MUST re-resolve (fail-closed) |
| Cache | `_cache` | Memory only | Lost (safe) |
| Idempotency | `_idem` (`tenant/name/key`) | Memory only, by design | Lost; a replayed `rotate` writes a new version unless `expected_version` (CAS) is used |
| Service state | `state` | Not persisted | `starting`; freeze/quarantine do not survive restart except boot-time audit quarantine (below) |
| Audit chain | `AuditChain.head/seq` | Audit file | `audit.resume_from_file` verifies the file and continues its chain |
| Vault token | `VaultProvider._token` | Memory | Re-login |

- `bootstrap.py::build_service` sets `state_path` to the audit path with suffix `.state.json`, so bootstrapped deployments always persist scopes and retirements. Direct constructions of `SecretsService` without `state_path` do not.
- State file format `inv55-state/1`; other formats are refused at init (`ValueError`). It contains tenants, names, app ids and versions — no secret values.
- Write-ahead: `set_scope`/`retire` persist the prospective state before mutating memory. If the write fails (e.g. disk full) the caller gets INTERNAL and nothing is applied — memory and file both keep the previous state (`tests/test_service_contract.py::LifecycleContract.test_state_write_failure_leaves_memory_unchanged`). Callers MAY simply retry.
- Audit resume: `resume_from_file` raises `ValueError` on divergence; `bootstrap.py` then starts a fresh in-memory chain object but transitions the service to `quarantined` (`audit_chain_divergence`) rather than serving. It never silently starts a new chain on a diverged file.
- Replay: lease ids are random (`secrets.token_urlsafe(24)`) and not persisted, so cannot be replayed across restart.

Evidence: `tests/test_service_contract.py::LifecycleContract.test_scopes_and_retirements_survive_restart`, `tests/test_config_audit_telemetry.py::AuditTests.test_file_sink_resume`.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Write-ahead state persistence |
| 4.3.0 | 2026-09-22 | Durable scopes/retirements, audit resume, boot quarantine |
