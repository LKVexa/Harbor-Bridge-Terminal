# INV-28 operations runbook (MC-067..MC-073)

Owner: `inv28-sre-owner`. Escalation goes to `inv28-component-owner` (ops/OWNERS.json). Severities: **SEV1** means production selection is unsafe or impossible; **SEV2** means production is degraded (refusals rising, a dependency is down); **SEV3** means no immediate impact.

## Day 0 / day 1 / day 2
- **Day 0:** load keys from the KMS into the `KeyRing` (purposes `registry`, `gap15`, `advisory`, `ticket`). Register the entries. Then `FileStore.save(registry.snapshot())`, confirm `readiness()`, and archive `evidence/RELEASE_EVIDENCE.json`.
- **Day 1:** run `python -B -m inv28_unikernel_implementations.tools.release_gate`. Roll out new toolchain versions with `RolloutController.plan` (canary, then staged, then all).
- **Day 2:** keep the advisory feed fresh (max age 2 days). Work `reviews_due` weekly. Check the dashboards in `ops/dashboards.json`.

## emergency-disable
1. Run `registry.emergency_disable("<name>@<version>", actor=<on-call>, reason="<ticket>")`. This needs the `emergency` capability and **no** revision precondition.
2. Confirm the entry shows `TC_DISABLED` in the explain view (`cli explain <decision>`) and that `INV28EmergencyDisableSelections` fires only for workloads that still ask for it.
3. `FileStore.save(snapshot)`, then announce to GAP-08 (`rollout.rollback`) if a rollout is in flight.
4. To re-enable: `transition(ref, "active", ...)` with `lifecycle` capability, after the fix is verified.

## rollback
- **Registry data:** `registry.rollback(<good revision>, actor, expected_revision, reason)` publishes the old entries as a *new* revision, so history is kept.
- **Rollout:** `rollout.rollback(ref, reason)` takes the version out of every cohort immediately. The GAP-08 announcement is retried from `pending_announcements` if the peer is down.
- **Component release:** redeploy the previous release archive, verify it with `SHA256SUMS.txt`, and load the last snapshot written by that release.

## backup-restore
- Backups are the `FileStore` directory (`rev-NNNNNN.json`, written atomically and append-only). Copy it off-host after every mutation batch and at least daily.
- **Restore:** `snap, problems = FileStore(dir).reconstruct(ring)`, then `Registry(ring).load(snap)`. Tampered or unreadable newer files are skipped and listed in `problems`. Treat any problem as a SEV2 security incident.
- **Drill:** `tests/test_resilience.py::Scenarios::test_control_plane_loss_restore_from_disk` and `tests/test_registry.py::IntegrityAndPersistence::test_backup_restore_reconstruct` run on every CI build.

## audit-rotation
The in-memory ledger is bounded at 100 000 entries. Persist it with `AuditLedger(path)`, rotate the file daily, and keep the last `entry_hash` as the anchor for the next file. Keep rotated files for `audit_retention_days` (ops/TELEMETRY_POLICY.json).

## refusal-spike
1. Look at the `Refusals by code` panel.
2. `TC_NOT_CERTIFIED` points to GAP-15. `TC_REVIEW_STALE` means reviews are due. `SEL_DEPENDENCY_UNAVAILABLE` means see dependency-unavailable.
3. If a recent rollout lines up with the spike, run `rollout.rollback`.

## dependency-unavailable
Production refuses on purpose while GAP-15 or the advisory feed is down (fail-closed). Restore the dependency. Do **not** weaken the policy. A waiver cannot cover certification or integrity.

## stale-reviews
Run `Inv28Service.reviews_due(now)`, then have the register owner schedule the reviews. The review cadence is per entry (`review.interval_days`).

## latency
Check the registry size against ops/CAPACITY.json and the cache hit rate. Rising p99 at a constant size is a regression, so bisect with `tools/bench.py`.

## cardinality
`inv28_metric_series_dropped_total` rising means a label value is unbounded. Find it in the exposition and fix the emitter. Do not raise `MAX_SERIES`.

## registry-burst
More than 50 revisions in 10 minutes. Confirm the actor in `registry.history`. If nobody expected it, treat it as SEV1 and revoke the actor's grants.

## maturity-breach
This should be impossible by construction. Query the audit ledger for `outcome=SELECTED` with `environment=production` and maturity other than `mature` and no waiver. Any hit is SEV1: emergency-disable the entry and escalate.

## Incident response (MC-073)
1. **Detect:** an alert fires, a report arrives through SECURITY.md, or an advisory is published.
2. **Triage:** assign a severity and open an incident record.
3. **Contain:** emergency-disable, roll back the rollout, or restore the snapshot.
4. **Communicate:** notify the workload owners of affected tenants through the escalation chain.
5. **Recover:** fix, re-review, re-certify with GAP-15, re-enable.
6. **Post-incident:** write the review within 5 business days, add a regression test, and update THREAT_MODEL.md if a new threat class appeared.

Paging: SEV1 pages `inv28-sre-owner` and `inv28-security-owner`. SEV2 pages `inv28-sre-owner`. SEV3 goes in the ticket queue.
