# INV-68 backup, restore, migration and reconstruction (MC-37; C095)

**Authoritative state** (ops/state_inventory.json): configuration snapshots, journal,
`ACTIVE` pointer + epoch, `FROZEN` marker, audit ledger + sealed anchor.
**Reconstructible:** placements (deterministic from request + config digest +
capacity), idempotency cache, rate windows, metrics.

| Objective | Value | Basis |
|---|---|---|
| RPO (config) | last committed activation | fsync before pointer swap |
| RPO (audit) | last flushed record; buffered records are counted if lost | audit.loss marker |
| RTO | seconds | restore = file copy + digest verification (drill: BACKUP_RESTORE.json) |

## Backup
`ConfigStore.export()` → `PK_PACK_CONFIG_BACKUP/1` JSON (all snapshots, journal,
pointer). Copy `audit.jsonl` + anchor after `AuditLog.seal()`. Schedule: on every
activation and daily; keep 90 days (proposed; service_owner to confirm).

## Restore
`ConfigStore.restore(new_root, bundle)` re-verifies every snapshot digest and refuses a
tampered bundle (`CONFIG_INVALID`). Then `inv68-audit verify audit.jsonl --anchor A
--key-env INV68_AUDIT_KEY`. Start the service; status must be `ok` (or `frozen` if the
marker was restored).

## Migration
Config schema changes ship a pure migration `PK_PACK_CONFIG/n → n+1` with digest
recorded in the journal `reason`; 4.3.0 introduces `PK_PACK_CONFIG/1` (no prior
config existed — 4.2.0 policy was in code).

## Drill
`python -m inv68_resource_packing.tools.drills` — export, destroy, restore, compare
digest and decisions, tamper test. Last result: evidence/BACKUP_RESTORE.json.
