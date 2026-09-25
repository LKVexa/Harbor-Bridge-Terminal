# Backup, restore, migration, reconstruction (M81)

State = `state.snapshot.json` + `state.wal` (+ `audit.jsonl`).
- **Backup:** call `StateStore.snapshot()`, then copy snapshot, WAL and ledger; record the ledger head `(seq, hash)` separately.
- **Restore:** place files in `state_dir`, start the fabric: snapshot loads, WAL entries after its seq replay, a torn final WAL line is ignored and counted (`torn_lines`). Links come back **revoked** and must be re-granted (fail closed). Verify the ledger against the recorded head.
- **Reconstruction without backups:** re-enrol hosts, re-push signed artifacts (the registry is content-addressed so refs are identical), re-start from desired state held by the deployment manager (INV-63).
- **Migration:** `inv60.state/1` only; any schema change ships a forward migrator and a documented non-rollback boundary (COMPATIBILITY.md).
- **Tested:** `tests/test_resilience.py::Durability`. **Not drilled** on real storage (W-DRILLS).
