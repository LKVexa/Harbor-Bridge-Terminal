# Backup, restore and reconstruction

**Protected datasets:** `state/journal/` (WAL, checkpoint, STATE_VERSION), `state/audit.jsonl`, `explain.jsonl`, `freshness.json`, `freezes.json`, the lease/fence files. The Git mirror is *reconstructable* from the remote and is not backed up.

| Objective | Proposed value | Basis |
|---|---|---|
| RPO | 0 for accepted syncs (journal fsync) / last backup for audit history | fsync per record |
| RTO | < 15 min (restore + recovery replay) | measured restore in tests is seconds |

**Format:** directory copy + `MANIFEST.json` (sha256 per file, state version, audit head). Encryption at rest: **BLOCKED** on a KMS/AEAD provider (stdlib has none) — store backups on encrypted volumes / object storage with server-side encryption and object lock (WORM) until then.

**Procedure:** `cli backup CONFIG DEST` → copy DEST off-site (same residency region, `ResidencyPolicy.check("backup", ...)`) → `cli restore BACKUP EMPTY_DIR` verifies every digest and refuses a non-empty destination (never overwrites newer state) → start the controller; recovery replays the journal and reads back ambiguous intents.

**Point-in-time:** the audit ledger + applied history + Git history reconstruct any past decision; a lost state directory can be rebuilt by a fresh sync from the approved ref (drift history is then lost — hence the backup).

**Isolated restore test:** `tests/test_apply_state.TestBackup` and `test_e2e.TestCLI` restore into a fresh directory each run.
