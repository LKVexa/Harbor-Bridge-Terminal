# Backup / restore / migration / reconstruction (checklist #94, DRAFT; restore drill NOT executed)

| State | Owner | Backup | Restore |
|---|---|---|---|
| Secret versions | Vault | Vault Raft snapshots (Vault operator) | Vault snapshot restore, then INV-55 restart |
| Scopes + retirements | INV-55 | `svc.state_snapshot()` JSON after every SCOPE/retire, stored with config | `svc.restore(snapshot)` (tested: `test_restart_invalidates_leases_keeps_scopes_and_retirements`) |
| Leases | none by design | not backed up | restart invalidates all leases (fail closed) |
| Audit chain | INV-55 | copy file + record head externally | `verify_file(expected_head=…)` before trusting |
| Configuration | git + provenance | provenance records | `ConfigController.rollback` or re-stage |

Migration to a new provider: add adapter → dual-read via `FailoverProvider` (new primary, old secondary) → copy versions preserving version numbers → switch → retire old. Reconstruction after total loss: restore Vault snapshot, restore scope snapshot, bootstrap, verify audit head continuity (a new chain starts if the old file is lost — record the break as an incident).
