# Incident response (MC-051-04..06, C097)

## Severity
| SEV | Definition | Page | Update cadence |
|---|---|---|---|
| 1 | writes unavailable, data loss/corruption suspected, cross-tenant exposure | immediately, owner + security | 30 min |
| 2 | degraded (frozen scope, p99 > SLO, replica lag > safe) | 15 min | 1 h |
| 3 | single non-critical feature impaired | business hours | daily |

Escalation: on-call → operations owner → engineering owner → security owner (SEV1 security). Communications: status channel + tenant notice for SEV1/2.

## Diagnosis tree (by alert)
* **INV05NotReady** → `GET /readyz` reason: `store_failed` ⇒ *Corruption/disk* branch; `quarantined`/`break_glass` ⇒ check audit for who/why; `draining` ⇒ rollout in progress.
* **Corruption/disk** → do NOT restart repeatedly. Quarantine (`/v1/admin/quarantine`), copy data dir + audit log to evidence storage, check `dmesg`/SMART, restore latest verified backup to a new dir, verify, switch.
* **INV05TxnConflictsHigh** → normal under contention; check a single hot key via explain records; escalate only with latency impact.
* **INV05SlowConsumers / WatchBacklog** → identify subject hashes in logs (`CS3001`), contact owning team; raise `limits.max_watch_queue_events` only with capacity review.
* **INV05CompactionLag** → verify controller running (heartbeat), protected revisions (`diagnostics`), stuck watchers.
* **INV05AuthFailuresSpike** → possible attack or cert expiry: inspect audit `authn` reasons, rotate/revoke, enable rate limits at the edge.
* **INV05ReplicaLag** → check network; if > safe lag, mark replica unsafe for reads.

## Containment that preserves evidence and correctness
Prefer `freeze writes` (reads continue) → `quarantine` (stop serving, keep data) → `break_glass` (whole data plane). Never delete WAL/snapshots/audit during an incident; copy first. Post-incident: verify audit chain, run invariants (`maintenance exit` requires them), file a review within 5 business days.
