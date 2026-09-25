# Runbook: Backup, restore, migration and disaster recovery (MC-042)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (restore rehearsals automated only in unit tests)

## Decision authority

Declaring disaster recovery and choosing a rollback point is the incident commander's decision with the service owner
(both UNASSIGNED - production blocker). Security must approve restoring from any backup older than the last audit checkpoint.

## Objectives and state inventory

See `controlplane/backup.py` `RPO_RTO`: authoritative (topology, ledger, txn journal, config, controls, audit),
reconstructable (entitlement from the upstream authority, explain), ephemeral (lease - re-elect; caches, latency).

## Backup

`backup(stores, path, signer=release_key)` on the leader: per-store snapshot under the store lock, sha256 per file,
Ed25519-signed manifest. Encryption at rest is NOT provided by this package (BLK-CRYPTO) - store archives only on
encrypted, access-controlled volumes.

## Rollback point selection

Prefer the newest backup whose manifest verifies AND whose audit head is not newer than the last trusted audit
checkpoint. For point-in-time needs use `LedgerStore.point_in_time(seq)` (read-only) to pick the sequence.

## Restore

1. `restore(archive, empty_dir, classes, trust=trust, dry_run=True)` - inspect stores, seqs, file counts.
2. `restore(..., dry_run=False)` into an EMPTY directory; heads must match the manifest.
3. Restore ordering (`RESTORE_ORDER`): controls, config, audit, topology, entitlement, ledger, txn, explain.

## Data-loss assessment

Compare restored heads/seqs with the last values seen in `/healthz/deep`, audit events and SCH-01 placement records;
every placement in SCH-01 without a committed claim (and vice versa) is a loss/drift item.

## Post-restore reconciliation

Run `PlacementCoordinator.recover_all()`, `LedgerStore` reconcile against SCH-01 placements, entitlement `reconcile()`,
GAP-02 `Inventory.reconcile()`; only then `DegradedPolicy.mark_reconciled()` and clear controls.

## Schema migration

`store.migrate(dry_run=True)` -> review plan -> `migrate(dry_run=False)`; the pre-migration snapshot is the rollback point.

## Escalation

Primary on-call -> secondary after 15 min -> service owner -> security on-call. Contacts UNASSIGNED.
