# Backup, restore, migration

| ID | INV55-OPS-BACKUP | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Data | Owner | Backup | Restore |
|---|---|---|---|
| Secret values/versions | Vault | Vault Raft snapshots (Vault procedure) | Vault snapshot restore; INV-55 cache expires within 30 s |
| Config layers | repo | version control | `activate` from tag; `ConfigController.rollback` in-process |
| Scopes + retirements | INV-55 | `SecretsService.export_state()` (format `inv55-state/1`, no secret values) or copy of `<audit>.state.json` | Place file at `state_path` before start; `_load_state` reloads it |
| Policy rules | host/deployer | declarative source outside INV-55 | `PolicyEngine.replace` at start (bootstrap starts with empty policy) |
| Audit log | INV-55 | copy file (append-only; hash-chained) | Restore file; `resume_from_file` verifies and continues; divergence → quarantined |
| Leases, cache, idempotency | — | not backed up by design | clients re-resolve |

- A restored state file older than the latest retirements re-enables versions retired since the backup. After restoring an older state file, operators MUST re-apply retirements recorded in the audit log (`op: "retire"`) or have used `destroy=true`.
- Migration between Vault clusters: copy KV data with Vault tooling, switch `provider.address` via overlay, restart. Version numbers may change; callers MUST re-read `expected_version`. Retired `(tenant,name,version)` entries refer to old numbers and MUST be reviewed. Automated reconstruction: NOT IMPLEMENTED.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | export_state/state file; audit resume |
