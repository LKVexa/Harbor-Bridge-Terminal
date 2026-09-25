# Runbook: Backup, Restore and Reconstruction

| Field | Value |
|---|---|
| Document ID | INV63-RB-BACKUP |
| INV-63 C-IDs covered | C095, C057 |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role), Security contact (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when the journal format changes. |

What is backed up: `journal.jsonl` only (source of truth). Not backed up: `epoch` (a restored instance acquires a fresh epoch), config (lives in `deploy/config`, versioned separately), secrets/keys (backed up by the secret store; a sealed journal is unreadable without its `data_key` kid).

## Backup
1. On the leader, call `svc.journal.backup(dest_dir)` (Python). It copies `journal.jsonl` (`shutil.copy2`) and writes `BACKUP.json` = `{schema: "INV63_BACKUP/1", records, head, sha256, taken_at}`.
2. Copy `dest_dir` off-host. Proposed schedule: daily + before every upgrade/rollout and always before `compact()` (pending approval). The snapshot keeps `previous_head` to match it to the backup.
3. `BACKUP.json` and journal envelope fields are plaintext; the data payloads are sealed only if a `Sealer` is configured. Protect backups as sensitive.
4. Verify periodically: restore into a scratch dir (below) — `Journal.verify()` equivalent.

Caveat: `backup` copies the file while the service may append; take it when no request is in flight or verify `records`/`head` match the restored file (restore enforces this).

## Restore
1. Stop the service (no writer on the target).
2. Target `state_dir` must be empty or have an empty `journal.jsonl` (else `INV63-E-PRECONDITION`).
3. Python: `Journal.restore(backup_dir, state_dir, sealer=<sealer or None>)` — checks SHA-256 against `BACKUP.json` (`INV63-E-STATE-CORRUPT` on mismatch), writes the journal, re-opens it with full chain verification, checks head == manifest head.
4. Start the service on `state_dir` with the same Sealer keys (required when `require_encryption_at_rest`); `_recover` replays and acquires epoch 1 (new directory has no `epoch`).
5. Any other instance still pointing at the **old** directory is not fenced by the new epoch (different file) — ensure it is stopped.
6. Run `svc.tick()`: actual lattice state is re-observed and corrected toward the restored desired state. Changes accepted after the backup point are lost (RPO = backup age).

## Reconstruction without a backup
Not supported by code. Desired state cannot be derived from the lattice (instances carry `ns`/version/host but not residency, spread, artifact signatures). Re-submit desired state from INV-64/INV-66 source of record.

## Migration
A compacted journal (leading `snapshot`) backs up/restores the same way. Journal format has no version field; any format change requires a migration tool (none exists). Moving hosts = backup + restore.

Test: `tests/test_service.py::DurabilityTest::test_backup_and_restore` (local temp dirs only).

Last exercised: NEVER — game day required
