# State classification, backup, restore, migration (v4.3.0)

| State | Class | Backup / reconstruction |
|---|---|---|
| Package code, schemas | immutable artifact | release archive + checksum |
| Active configuration + history | durable (source of truth is the config repository) | re-activate from repo by digest |
| Route policy registries, revisions | reconstructable | sealed `PK_MESH_SNAPSHOT/1` (`svc.snapshot()`) |
| Fencing tokens, freeze/quarantine | reconstructable | in the same snapshot |
| Bypass evidence | ephemeral (evidence copy in audit) | not restored; audit holds each flag |
| Audit trail | durable when JSONL sink configured | append-only file + externally recorded head |
| Idempotency cache, decision journal | ephemeral | not restored (RR-08) |

**Backup:** take `svc.snapshot()` on every successful migration batch and at least hourly; store beside the audit head.
**Restore:** `svc.restore(operator_token, snapshot)` → seal verified, every policy re-validated against retry invariants, tenant capacity enforced, undeclared tenants skipped, applied all-or-nothing, audited (`state.restored`).
**Migration (version change):** snapshots carry `version`; a new major that changes the body schema must ship a converter and keep reading the previous schema for one minor.
**Validation:** after restore, compare `revisions` and route counts with the snapshot; run `audit_export` and verify.
