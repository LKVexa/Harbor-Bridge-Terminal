# INV-57 Operator Runbooks (v4.3.0 — DRAFT, not rehearsed)

These runbooks describe procedures that the v4.3.0 code supports. None has been rehearsed against a
production-equivalent environment, so MC-59/MC-62/MC-63 stay open until someone rehearses them and
records the evidence.

## Day 0 — install

1. `pip install inv57-durable-execution-4.3.0-py3-none-any.whl` (build: `python -m build`, see `ci.sh`).
2. Write a config document and validate it: `python -m inv57_durable_execution config-validate cfg.json`.
3. Activate it through `ConfigManager.activate(doc, actor=..., reason=...)`. This writes `active.json`
   atomically and appends a hash-chained record to `config-ledger.jsonl`.
4. Check readiness: `python -m inv57_durable_execution status --db <state_path>` (exit 0 = ready, 3 = not ready).

## Day 1 — run

- Each worker acquires a lease per workflow (`SQLiteBackend.acquire`) and renews it before `lease_ttl_seconds`
  runs out. An expired lease makes every later append fail with `INV57-E010 StaleOwner`, which is expected:
  the worker must stop.
- Metrics: `replays_total`, `nondeterminism_total`, `activities_executed_total`, `run_errors_total{code}`.

## Day 2 — procedures

| Situation | Signal | Action |
|---|---|---|
| Activity in doubt | `INV57-E005` | Run `effects.reconcile_in_doubt(worker, provider)`. If it raises `INV57-E020`, establish the real outcome with the provider, then call `Worker.resolve_in_doubt(activity_id, result)`. Never re-run the activity by hand. |
| Non-determinism | `INV57-E001` | Deploy the previous workflow code version, or restart the workflow as a new run (`identity.next_run()`). Do not edit history. |
| Quarantined history | `INV57-E013` | Preserve the DB file. Compare against the latest backup manifest. Release only with `release_quarantine(capabilities=["operator"])` after review. |
| Bad configuration | readiness `config:*` | `ConfigManager.rollback(<digest from ledger>, actor, reason)`. The rollback is recorded in the ledger. |
| Emergency disable | — | Set `StatusSurface.frozen_reason`, which drops readiness, and apply `suspend` to affected workflows. Deployment-level disable is BLOCKED (RG-05). |
| Overload | `INV57-E018` | Check `AdmissionController.snapshot()` and raise per-tenant limits only through the config ledger. |

## Backup / restore (MC-61)

```python
manifest = backend.backup("/backups/inv57-2026-09-23.db")         # online, consistent
json.dump(manifest, open("/backups/inv57-2026-09-23.manifest.json", "w"))
restored = SQLiteBackend.restore(backup, "/new/path.db", manifest)  # verifies chains + tails
```

Restore always goes to a fresh path. It resets leases and advances every epoch by 1000, so workers from
before the backup are fenced out. Store the manifest separately from the backup: it is the only defence
against tail truncation.

## Incident severity (MC-63 draft; paging integration BLOCKED)

| Sev | Definition | Examples |
|---|---|---|
| 1 | Possible duplicate external effect, or cross-tenant exposure | `unsafe` effect in doubt with money movement |
| 2 | Integrity failure or quarantine | `INV57-E013`, `INV57-E002` |
| 3 | Availability degraded | readiness false, circuit open |
| 4 | Single-workflow non-determinism | `INV57-E001` |

Escalation targets: **unresolved**. `OWNERS.yaml` has no named roles yet (MC-01 BLOCKED).
