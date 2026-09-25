# INV-72 operator runbook (C040, C092, C095, C096)

Owners and escalation: `ops/OWNERS.md`, `ops/ESCALATION.json`. Incidents: `ops/INCIDENT.md`.

## Day 0 — bootstrap from an empty environment (C040)

Prerequisites: CPython 3.10–3.13; nothing else (runtime is stdlib-only).

```bash
python -B -m inv72_accelerated_workload_requirement.tools.bootstrap --profile datacenter --journal /var/lib/inv72/journal.jsonl
```

`tools/bootstrap.py` is deterministic: validate profile → activate generation 1 → wire a discovery
source → refresh → start the store (recovering the journal if present) → print PK_ACCEL_STATUS/1.
Exit 0 only when `ready` is true. With no keys configured it uses an in-process demo key and says so;
production must pass real keys through the host `KeyProvider`.

Health checks: `status()["ready"]`, `status()["reasons"]` (empty when healthy).

## Day 1 — deployment and staged rollout (C092)

1. Verify the archive: `python -B -m <pkg>.tools.manifest --verify` → `MANIFEST OK`.
2. **Canary:** one instance per site with the new version, `take_leadership(fence=N+1)` on a *separate*
   store (shadow) and `reserve=False` traffic mirrored from GAP-11 for 30 min. Compare refusal-code
   distribution against the old version (dashboard "Refusals by reason code"); any new code class → stop.
3. **Stage:** 10 % → 50 % → 100 % of sites, 1 h soak each, gated on alerts A-LATENCY/A-SHED silent.
4. Mixed versions are safe inside the `compat.peer_supported` window (same major, minor ±1).

Rollback: redeploy previous archive; configuration rollback is independent:
`ConfigStore.rollback(author=…, reason=…)`. Automatic rollback: `activate(…, probe=fn)`.

**Emergency disable:** `service.disable(reason, token=<operator>)` → every request returns
`ACCEL_DISABLED` (terminal, GAP-11 stops queueing); existing reservations are untouched.
Re-enable: `service.enable(token=…)`. Device-level: `quarantine(dev, reason, revoke=True)`.

## Day 2 — operations

| Task | Command / API | Check |
|---|---|---|
| drain a device for maintenance | `drain(dev_id, reason)` | device absent from new selections; existing kept |
| pull a faulty device | `quarantine(dev_id, reason, revoke=True)` | reservations revoked, audited |
| config change | `ConfigStore.activate(candidate, author, reason, probe=…)` | provenance in audit (`config.activated`) |
| inventory stuck stale | check `status()["inventory"]["last_error"]`; fix GAP-02 source; `refresh()` | state `fresh` |
| controller failover | new leader `take_leadership(fence=old+1)` | old leader gets `ACCEL_STALE_FENCE` |
| export audit | `audit.export()` → durable sink; record `head()` externally | `AuditLog.verify(..., expect_head=…)` |

## Backup, restore, migration, reconstruction (C095)

* **Backup:** `store.snapshot()` (self-digested PK_ACCEL_STATE_SNAPSHOT/1) plus the journal file.
* **Restore:** `ReservationStore.restore(snapshot, journal_path=…)`; a tampered snapshot is refused.
* **Crash recovery:** `ReservationStore.recover(journal)` — torn tail truncated and reported, any
  earlier corruption refused (`ACCEL_STATE_CORRUPT`) → restore from snapshot.
* **Reconstruction with no backup:** reservations are soft state owned by GAP-11's job records;
  rebuild by replaying GAP-11's running jobs as `request(…, idempotency_key=<job id>)`.
* **Migration across versions:** snapshot schema is versioned; an unknown schema is refused.

## Drills

None has been run (no named operators). W-007 tracks it.
