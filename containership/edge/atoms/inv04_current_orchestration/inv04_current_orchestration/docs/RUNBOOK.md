# INV-04 Operator Runbook (v4.3.0)

- **Status:** Draft. Needs game-day validation (#74) and on-call routing from `docs/OWNERS.md` (#75).

## Day 0 — bootstrap

1. Install: `pip install .` (stdlib-only runtime) and verify the release with `python tools/release.py --verify --out <dist>`.
2. Validate the config before first start. `load_config()` rejects unknown keys and out-of-bounds values. Keep the base config, environment overlay, and site overlay as separate files.
3. Start one replica. `/healthz` returns 200 once started. `/readyz` returns 200 only when this replica is the leader and API discovery succeeds.
4. Run `python tools/evidence_gate.py` and `python tools/pk_core_gate.py`, and archive the output with the release.

## Day 1 — deploy

- Run two or more replicas per site. Exactly one holds the lease (`inv04_leader == 1`).
- Keep the feature gates `drain`, `reconcile` and `handoff` off until canary validation is done. Apply config changes through `ConfigManager.apply` with an issuer. A failed health check reverts automatically.

## Day 2 — operate

### Signals

| Metric | Meaning | Action |
|---|---|---|
| `inv04_replica_drift{workload}` ≠ 0 for >30 s | Convergence SLO at risk | See "Stuck reconciliation" |
| `inv04_drains_total{outcome="rejected",reason="budget_breach"}` | Safety refusal (expected) | Scale the workload or relax its PDB with the owning team |
| `inv04_drains_total{outcome="failed_cordoned"}` | Drain stopped after the point of no return | See "Drain failed cordoned" |
| `inv04_capacity_failures_total` | No room to re-home | Add capacity; do not force |
| `inv04_workqueue_oldest_seconds` rising | Stall or backpressure | See "Stuck reconciliation" |
| `inv04_api_errors_total{code="ORCH_NOT_LEADER"}` spikes | Leader flapping | See "Leader loss" |

### Alerts

`drain_budget_breach` (page, never suppressed), `convergence_fast_burn` (14.4× over 1h and 5m, page), `convergence_slow_burn` (6× over 6h and 30m, page), `convergence_drift` (1× over 3d and 6h, ticket). During declared maintenance, pages drop to tickets, except budget breaches.

### Procedures

**Drain rejected (`budget_breach`, `no_capacity`, `drain_policy`).** Nothing changed: rejection happens before cordon. Read `blocked` in the response.
- `unmanaged_pod`: confirm the pod can be lost, then retry with `force_unmanaged=true` under a new idempotency key.
- `local_storage`: confirm the data is disposable, then use `delete_emptydir_data=true`.

**Drain `uncordoned` (aborted before first eviction).** The cordon was rolled back automatically. Check `reason` (`eviction_failed:<code>`, `cordon_failed:<code>`, `node_partitioned`) and retry after the dependency recovers.

**Drain `failed_cordoned`.** At least one pod was evicted, so the node stays cordoned on purpose.
1. Check replacements: `GET /v1/inventory`.
2. Once the cause is fixed, retry with the same `idempotency_key` only if the earlier call never returned. Otherwise use a new key.
3. Uncordon by hand only after confirming no workload depends on the node staying out of rotation.

**Process crash mid-drain.** Nothing to do. The next leader runs `recover()` at start and finishes or rolls back every open operation from the journal. Check the `recovering` phase entries in the journal.

**Watch desynchronisation / stale cache.** An `ORCH_STALE_CACHE` error or rising `inv04_informer_lag` means the informer relists automatically on `Gone`. If lag persists, restart the replica; leadership fails over.

**Leader loss or flapping.** Check clock sync, API-server latency, and whether `renew_deadline_s < lease_seconds`. A stale ex-leader is fenced (`ORCH_FENCED`) and cannot mutate.

**Stuck reconciliation.** `StallDetector` reports `no_progress` or `repeated_conflicts` per key. For repeated conflicts, look for a second controller writing the same objects. Check the `OwnershipRegistry` during migration.

**Stuck-terminating pods.** `termination_state` = `stuck_terminating` or `finalizer_blocked`. Force deletion is an operator action only (`kubectl delete --force --grace-period=0`), and only after confirming the node is really gone. Never automate it.

**Journal corrupt (`ORCH_JOURNAL_CORRUPT`).** Stop all replicas and preserve the file. Only the torn last line is auto-repaired; tampering or mid-file corruption needs forensic review. Restore from backup and replay manually.

### Emergency disable

Set feature gates `drain=false` and `reconcile=false` through `ConfigManager.apply(issuer=...)`. The change takes effect on activation and is recorded with provenance. As a last resort, scale replicas to 0. The incumbent control plane keeps running; INV-04 never deletes workloads on shutdown.

### Rollback

See `docs/ROLLBACK.md`.
