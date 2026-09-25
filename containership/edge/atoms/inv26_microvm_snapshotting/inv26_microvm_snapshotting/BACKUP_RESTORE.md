# Backup, restore, migration and reconstruction (C095)

* **Metadata:** `MetaStore.export()` → checksummed JSON (records incl. wrapped DEKs, grants, config history,
  seq and fence). `MetaStore.import_backup(root, backup)` refuses a tampered checksum and refuses to overwrite
  existing metadata. Drill: `tools/drills.py backup_restore` (3 snapshots restore after import; a consumed
  grant stays consumed).
* **Blobs:** ciphertext; back up with the storage system. Useless without the KEK.
* **KEKs:** owned by the KMS; losing the KEK = losing every snapshot under it (by design; crypto-erase).
* **Reconstruction after loss of metadata without backup:** not possible by design — blobs cannot be decrypted
  without the wrapped DEKs; snapshots must be re-captured (snapshots are a cache of boot state, not a system of
  record).
* **Migration across schema majors:** export → upgrade → import is supported within `PK_SNAPSHOT_METASTORE/1`;
  VMM state files are never migrated (re-capture).
* **Scrub:** `SnapshotService.scrub()` re-verifies every AVAILABLE blob digest and quarantines mismatches.
