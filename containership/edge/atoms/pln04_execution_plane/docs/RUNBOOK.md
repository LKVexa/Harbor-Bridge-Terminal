# PLN-04 runbook (day-0 / day-1 / day-2 / incident)

Owner and on-call are **UNASSIGNED** (ops/OWNERS.json). Every page below goes to the rotation named there once it is assigned.

## Day 0 — bootstrap from an empty node (PLN-04-C040)

1. Validate the config: `python -c "from pln04_execution_plane.policy import PlaneConfig as C; print(C.from_file('config/production.json').generation)"`.
2. Provision secrets: signing keys for actor, classification, provenance and attestation roots, delivered via `FileSecretProvider` on a 0600 tmpfs.
3. Create the state directory (0700) and the audit path. Configure the external audit anchor.
4. Register exactly one approved provider per tier (ADR-0001). The registry rejects duplicates and, in production, reference providers.
5. Construct `ExecutionPlane(profile=production)`. The constructor refuses to start if any production control is missing.
6. Run `recover()`, then `reap()`. For each tier: `challenge()`, obtain evidence, then `attest_tier()`.
7. Check `/readyz` shows `ready: true`. Set rollout to `canary`.

## Day 1 — deploy a new version

1. Run the release gate: `tools/release_gate.py`. Only GO ships. NO_GO lists the blockers.
2. Canary: set `enable("canary", [tenants])`. Watch the alerts in ops/alerts.json for 30 min.
3. Promote: `enable("full")`. `auto_rollback()` is evaluated every minute by the host loop.

## Day 2 — routine

| Task | Cadence | Command / API |
|---|---|---|
| Attestation refresh | < `attestation.max_age_s` | `refresh_attestation()` + re-attest each tier |
| Reaper (includes idempotency pruning) | 1 min | `reap()` |
| State compaction + backup | hourly / daily | `store.compact()`, `store.backup(path)` → off-node |
| Audit anchor | per 64 events + hourly | `audit.anchor_now()` |
| Event export flush | continuous | `exporter.flush()` |
| Review access, policy, deps, config, arch (PLN-04-C098) | quarterly | ops review; update WAIVERS.json |

## Incidents (PLN-04-C097)

| Severity | Trigger | Containment | Recovery |
|---|---|---|---|
| SEV1 | split-brain alert, hostile-tier escape suspicion, audit chain break | `emergency_disable()`, then `drain()` affected nodes; preserve the audit file and anchors | Verify the chain with `verify_audit_file(path, anchors)`. Restore state from backup if corrupt. Re-attest. |
| SEV2 | attestation failure on a tier; provider error ratio > 5 % | tier auto-fails closed; `auto_rollback()` | Fix the provider, re-attest, and recreate quarantined workloads (never resume them) |
| SEV3 | reaper stuck > 30 min; export backpressure | investigate the provider zeroization receipts | `reap()` after the provider fix. Stuck resources stay withheld until then. |

### Split-brain (PLN-04-C058)

A second controller claiming a live lease raises `split_brain_detected`. The lower-epoch controller's provider commands are already rejected (PLN04-STATE-002). Stop the stale controller. Do **not** delete lease records by hand, because the global epoch counter must stay monotonic.

### Restore from backup (PLN-04-C095)

1. Quiesce: `emergency_disable()`.
2. `FileStateStore.restore(backup)`. The checksum is verified; a mismatch aborts.
3. `recover()`: anything not confirmed running by its provider becomes orphaned or failed.
4. `reap()`, re-attest, then `enable()`.
