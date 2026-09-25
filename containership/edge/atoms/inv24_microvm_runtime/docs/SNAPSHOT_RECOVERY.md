# Snapshot and recovery (MC-004, MC-059)

Protocol and invariants: `inv24_microvm_runtime/snapshot/store.py` module docstring.

## Restore procedure
1. `validate_for_restore(id, tenant, workload, current_epoch, device_model)` — any failure: do **not** launch; fall back to cold boot.
2. Acquire the instance lease; pass the new epoch into the restored instance's ownership record.
3. Load via Firecracker `/snapshot/load` (adapter call pending approved Firecracker version — BLOCKED).
4. On any error: stop VMM, release ownership, keep snapshot for forensics, emit audit event.

## Reconstruction after node loss
- Instance state is **not** reconstructed from memory; workloads are re-admitted by PLN-04 using the same operation keys (idempotent).
- Journal (`ops.jsonl`) + leases (`leases.json`) + config history + audit log are the durable state; back them up hourly off-node (`RUNBOOKS.md` §Backup).
- `AdmissionController.reconcile(live)` drops reservations for dead instances; `OwnershipRegistry.reconcile(live)` frees their devices; `SnapshotStore.gc_partials()` removes torn snapshots.
