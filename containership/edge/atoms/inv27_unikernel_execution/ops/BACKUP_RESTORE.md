# Backup, restore, migration, reconstruction (MC-037; C095)

| State | Backup | Restore / reconstruct |
|---|---|---|
| Instance journal (`Journal`, HMAC-chained JSONL when `journal_key` is supplied — required in prod) | copy the file; optionally `sealed_store.seal` it | start the service with `journal_path`. Replay verifies the chain (`UK_STATE_CORRUPT` on tamper) and tolerates one torn final line. |
| Audit log | `AuditLog.export()`, with the head anchored in release evidence | `AuditLog.verify(events, expect_head=...)` |
| Config generations | `ConfigStore.history` export | re-apply the generations in order; `verify_history()` |
| Trust root | secret store (authoritative) | reload; no local state |

**Migration.** Journal records are versionless JSON lines keyed by field name. A new field is
additive; a removed field needs a MAJOR release and a conversion script.

**Reconstruction when the journal is lost.** Instances cannot be resumed: their VMM processes died
with the controller. Re-run is safe because `run` is idempotent per (tenant, key) only within a
journal, so callers must re-submit.

The restore drill has not been run (W-DRILLS).
