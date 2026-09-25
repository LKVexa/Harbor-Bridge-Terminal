# INV-04 Release Rollback (component 71)

- **Status:** Documented. Not rehearsed.

## 4.3.0 → 4.2.0 compatibility

| Surface | 4.3.0 change | Rollback impact |
|---|---|---|
| `model.Cluster` API | Unchanged | None |
| PK_ORCH_RECONCILE/1, PK_ORCH_INVENTORY/1 | Unchanged (`x-revision` metadata only) | None |
| PK_ORCH_DRAIN/1 | Optional 1.1 fields (`idempotency_key`, `dry_run`, …), negotiated | 4.2.0 has no transport; clients must stop sending 1.1 fields |
| PK_ORCH_ERROR/1 | Additive codes plus optional `details` | 4.2.0 consumers must tolerate unknown codes |
| New state: journal JSONL, VersionedStore JSONL | New in 4.3.0 | 4.2.0 ignores them. **Finish or abort open drains before rolling back** (`open_operations` must be empty). |

## Procedure

1. Set the `drain` and `reconcile` feature gates to false. Wait until `Journal.open_operations(TERMINAL)` is empty.
2. Archive the journal files as evidence. Do not delete them; they remain the audit trail.
3. Install the 4.2.0 artifact (verify its MANIFEST.sha256) and run `tests/test_model.py` under both normal and `-O`.
4. Record the rollback in the audit trail (`AuditTrail.record(action="rollback", ...)`) from the new-version host before uninstalling, or in the change record.

## Roll forward again

Reinstall 4.3.0. The journal replays, config provenance restores the last activated config, and the idempotency registry reloads.
