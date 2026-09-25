# Backup, restore, migration and reconstruction (MC-32; C095)

State inventory: `ops/state_inventory.json` (source of truth; summary below).

| State | Authoritative? | Backup | RPO / RTO |
|---|---|---|---|
| ConfigStore (`state.json` + `journal.jsonl`) per target | yes | required, after every commit (`tools/backup_restore.py backup`; a copy taken mid-transaction is still consistent: an unfinished PREPARE is aborted by recovery on restore, a journaled COMMIT is rolled forward) | RPO: last commit · RTO: 15 min |
| audit ledger + anchor | yes (security) | required, shipped to WORM storage; never rebuilt | RPO: 5 min · RTO: 1 h |
| tenant registry, idempotency/replay/rate tables | no (reconstructible / ephemeral) | no | n/a |
| decision log, logs, metrics | no (telemetry retention applies) | no | n/a |
| policies, trust policy | yes, but owned by their source repository | source control | n/a |
| release evidence | yes | retained with the release | n/a |

## Procedures

```
python -m inv64_application_model.tools.backup_restore backup  --store STORE_DIR --audit audit.jsonl [--anchor anchor.json] --out inv64-<target>-<date>.tar
python -m inv64_application_model.tools.backup_restore restore --backup inv64-<target>-<date>.tar --into NEW_EMPTY_DIR --tenant <tenant>
```

Restore never writes over live state: it requires an empty target, verifies
every file digest from `BACKUP_MANIFEST.json`, the audit hash chain (and
anchor when the key is supplied), that the active revision's digest re-derives
from its manifest, the software major version, and — with `--tenant` — that no
revision belongs to another tenant. Only after PASS does the operator stop the
service, swap directories, and start it (ops/RUNBOOK.md §Day-2 restore).

**Encryption/access:** backups contain tenant topology (confidential): store
them in an access-controlled bucket with server-side encryption, or seal with
`crypto_policy.seal` before upload. Retired backups are deleted after 90 days
(configuration) / retained with the audit retention (ledger); deletion is
logged.

## Migration

Backup format `PK_APP_BACKUP/1` records software and schema versions.
4.x → 4.x restores are compatible; a major-version mismatch fails restore.
Future schema migrations MUST ship a forward migration and either a backward
migration or an explicit "irreversible" marker, both tested before release.
No migration exists yet (4.3.0 is the first version with persistent state).

## Reconstruction

Registry: re-derive from `app.submit accepted` audit records or resubmission.
ConfigStore: not reconstructible without backups (effective configs live only
there) — reconstruction fails safely (store refuses to start on corrupt state;
`tools/faults.py` f13).
