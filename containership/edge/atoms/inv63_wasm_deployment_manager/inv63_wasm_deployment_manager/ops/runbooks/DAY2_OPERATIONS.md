# Runbook: Day-2 Operations

| Field | Value |
|---|---|
| Document ID | INV63-RB-DAY2 |
| INV-63 C-IDs covered | C071, C077, C096 |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change. |

## Routine
| Task | How | Expected |
|---|---|---|
| Control loop | scheduler calls `svc.tick()` every `reconcile_interval_s` (30 s default; 120 s on `edge-site-a`). **No scheduler is bundled.** | runs `resync()` first if intents are pending; `results` per namespace; frozen/quarantined skipped; `stalled` list |
| Health | `svc.status()` | `live`, `ready`, `leader`, `epoch`, `degraded`, `config_digest`, `dependencies{lattice,journal,breaker}`, `capabilities`, `controls`, `stalled`, `preflight` |
| After lattice outage | automatic in next `tick()`, or `svc.resync()` | `{"resynced": [...], "pending": 0}` |
| Metrics | scrape `svc.metrics.exposition()` (B-13); dashboard `observability/dashboard.json` | see `CAPACITY_MODEL.md` |
| Why did it do that? | request op `explain` `{tenant, component}` (role with `explain:read`) | `INV63_EXPLAIN/1`: action, why, inputs, policies, constraints, trace_id, release, topology (in-memory; lost on restart) |
| Backups | `BACKUP_RESTORE.md`, daily (proposed) | `BACKUP.json` manifest |
| Journal size | check `ls -l <state_dir>/journal.jsonl` vs 256 MiB (no metric exists) | at ~80%: backup, then `svc.compact()` (leader only) → `{records_before, records_after: 1, head}`. Compaction removes prior `desired_set` versions needed by operator `rollback` |
| Config change | `ConfigStore.activate(layers, author, reason)`; rollback `ConfigStore.rollback(author)`; restart service with new config (no hot reload) | new `Activation.digest` equals `config.config_digest` of composed config |
| Key rotation | `TokenAuthority.rotate(kid, key)` then `retire(old)` after max TTL; `Sealer.rotate` + `reseal` | `test_security.py::AuthNTest::test_key_rotation` |
| Node maintenance | `svc.quarantine_host(host, True, principal)` (tenant `*`, `control:quarantine`) → `tick()` moves instances off → maintain → `quarantine_host(host, False, principal)` | instances re-spread |

## Alert response (`observability/alerts.json`)
| Alert | First action |
|---|---|
| `INV63ControlPlaneDown` (SEV2) | check Wadm/NATS; service is in offline mode; watch `offline_autonomy_s`; after recovery `tick()` resyncs automatically |
| `INV63Stalled` (SEV2) | `status().stalled`; `explain` each; check start failures (`PARTIAL`), capacity, quarantined hosts |
| `INV63SecurityEvents` (SEV2) | `INCIDENT.md`; inspect `request_failed` logs by `code` / `subject` |
| `INV63Degraded` (SEV3) | shedding: check load, `max_inflight`, callers retrying without backoff |
| `INV63PolicyRejections` (ticket) | residency config vs tenant requests |

Last exercised: NEVER — game day required
