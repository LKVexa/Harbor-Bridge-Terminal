# GAP-10 Operations Runbook

Covers deployment, rollback, emergency disable, troubleshooting, and backup/restore (component 38). Anchors below are referenced by `ops/alerts.json`.

## Deploy

1. Build: `python tools/build_release.py --out dist --source-revision <sha> --key-file <release.key>`; verify with `build_release.verify`.
2. Run the full suite on the pinned build: `python tools/run_all_tests.py` (writes `evidence/TEST_REPORT.json`).
3. Register hardware classes in the calibration inventory; any node without one runs on the conservative profile.
4. Start one controller per shard; confirm `health()["ready"]` and `safe_to_enforce`.
5. Roll policy out with `RolloutController` (1% → 5% → 25% → 100%, 10-minute soak, guards on exclusions/divergence).

## Rollback

- **Policy:** `PolicyService.rollback(scope)` restores the previous revision atomically (audited `policy.rolled_back`).
- **Code:** redeploy the previous signed artifact; state records are forward/backward compatible (`PK_THERMAL_NODE_STATE/1`). Restarted controllers resume at `max(persisted, critical)`.

## Emergency disable {#controls}

Apply a signed `emergency-disable` control with target `*`. Automation continues computing, but every node is capped at `disable_fraction` (0.25) and decisions carry `automation_disabled: true`. Release requires `control.release`. Quarantine (ceiling 0) and freeze (no increase) work per node. Controls never raise capacity.

## Alerts → actions

### Derating {#derating}
Informational. Use `explain(node)` to confirm the limiting input.

### Exclusion {#exclusion}
Node over emergency. Check the source sample and cooling; do not override. Node readmits only after fresh telemetry clears the 5 °C / 5 pp recovery margin.

### Stale telemetry {#stale-telemetry}
GAP-09 silent or rejected. Check `telemetry.health()` counters (stale/future/bad_signature). Node stays constrained until fresh trusted samples arrive.

### Cooling domain {#cooling-domain}
Majority of a rack/room constrained or inlet over limit. Engage facilities. Treat as a physical incident.

### Battery {#battery}
Runtime above reserve below threshold. Confirm mains status; shed per shedding policy.

### Forged input {#forged-input}
Bad signature / unauthorized scope / replay. Treat as a security incident (SEV2): identify key id from the audit `security.failure` records, revoke if compromised (`KeyRing.revoke`), rotate reporter keys.

### Divergence {#divergence}
Scheduler applied limit ≠ GAP-10 desired limit. SEV1: quarantine affected nodes, re-run `SchedulerEnforcementAdapter.apply`, inspect the scheduler.

### Not safe to enforce {#not-safe}
Inspect `health()["checks"]`: leader, clock_trusted, state_store, telemetry_fresh, policy_active. Consumers are already failing closed.

### Dependencies {#dependencies}
Circuit breaker open on the state store. Decisions are capped at critical until the store recovers.

### Latency {#latency}
p99 above budget. Run `tools/bench.py` on the host; check store fsync latency.

### Fleet-wide {#fleet-wide}
Over 30% derated. Check for a bad policy rollout first (roll back), then weather/facility events.

## Backup, restore and reconstruction (component 38) {#backup}

1. **Backup:** `digest = store.backup("state-YYYYMMDD.tgz")`; store the digest with the audit head (`AuditSink.head`) off-host.
2. **Restore:** `FileStateStore.restore(archive, new_root, digest)` rejects digest mismatches and unsafe archive members.
3. **Verify the audit chain:** `AuditSink.verify(entries, anchored_head)` must return ok.
4. **Recover ownership:** stop all old controllers; start the new one; `acquire()` issues a strictly greater fencing token, so any surviving old writer is fenced out of the store and consumers.
5. **Verify downstream before reopening:** restored nodes resume at `max(persisted, critical)`. Run `adapter.divergence(node)` for every node and require zero divergence. Placement reopens only as fresh trusted telemetry arrives.
6. **Reconstruction without a backup:** start empty. Every node starts `critical` and converges from live telemetry; policy is reloaded from the policy service; no capacity is reopened on guesswork.

## Recovery objectives (RTO / RPO) {#rto-rpo}

| State | RPO | RTO | Basis |
|---|---|---|---|
| Per-node decision state | 0 (each decision fsynced before publish) | lease TTL + one telemetry interval (≈40 s default) | `FileStateStore.save` atomic write; new leader acquires after TTL |
| Policy revisions | 0 for activated revisions (audited) | minutes (restore from audit + policy source) | revisions are content-addressed and re-submittable |
| Audit chain | last fsynced entry | minutes | head anchored off-host |
| Consumer view | n/a (derived) | immediate: consumers fail closed until republished | `CeilingView` |

During any recovery window capacity is *restricted*, never reopened.

## Troubleshooting quick reference

| Symptom | First check |
|---|---|
| Node stuck critical | `explain(node)`: missing sensor kind, untrusted clock, store unhealthy, hysteresis |
| All admissions denied | `CeilingView.effective()` reason: GAP-10 unhealthy, stale decisions |
| Policy won't activate | `POLICY_REVISION_CONFLICT` (stale parent) or `POLICY_UNAUTHORIZED` (relaxation needs a second approver) |
| Controller refuses to decide | `OWNERSHIP_CONFLICT` / `FENCING_TOKEN_STALE`: another leader holds the shard |
