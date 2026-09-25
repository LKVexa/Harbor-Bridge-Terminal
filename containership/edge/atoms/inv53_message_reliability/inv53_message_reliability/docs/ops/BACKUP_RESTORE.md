# Backup, restore, migration and reconstruction (C095)

- **Backup (online-safe via the owning process, or offline via CLI):** `store backup STORE_DIR DEST` → compacts,
  copies `snapshot.json` + `journal.jsonl`, writes `MANIFEST.json` with file sha256s and the state digest.
- **Restore:** `store restore BACKUP_DIR NEW_EMPTY_DIR` → verifies every file hash, refuses a non-empty target,
  replays, compares the state digest with the manifest; refuses on any mismatch.
- **Migration:** a new store schema registers a migration in `DurableQueue._migrate`; restore of an unknown
  schema is refused.
- **Reconstruction when no backup exists:** the journal is a complete, hash-chained history since the last
  snapshot; if only the journal survives, delete nothing — open it (a torn tail is truncated automatically).
  If the snapshot is lost but an older backup exists, restore the backup and have producers re-send
  (idempotent puts return `OK_DUPLICATE` for what survived).
- **RPO/RTO:** RPO = 0 for acknowledged operations with `fsync=true` on healthy media; RTO = replay time
  (measured by the drill in `test_repository.py::DrillTest`). Targets are PROPOSED.
