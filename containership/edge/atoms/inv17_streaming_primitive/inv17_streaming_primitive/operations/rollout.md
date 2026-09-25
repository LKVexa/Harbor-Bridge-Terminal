# INV-17 Canary / Staged Rollout and Rollback

**Controls:** C092 (checklist §55). Automation: tools/rollout.py (planned); gate inputs from tools/perf_gate.py, tools/exit_gate.py.

No rollout has been executed with this procedure. Stage durations and thresholds are PROPOSED.

## 1. Stages

| Stage | Scope | Min soak (PROPOSED) | Promote if |
|-------|-------|---------------------|-----------|
| 0 | CI: tests, coverage (tools/coverage_run.py), perf gate, exit gate | – | all green |
| 1 | dev tier (`environment: dev`) | 1 h | `/readyz` 200, no new error codes |
| 2 | Canary: 1 production instance per tier (cloud, far-edge overlays) | 24 h | health not `unhealthy`; stall ratio and `inv17_load_shed_total` rate not worse than baseline; no `auth.*`/`trust.unavailable` increase |
| 3 | 25 % of instances | 24 h | same |
| 4 | 100 % | – | – |

Compare canary to baseline using `/metrics` with release-lineage labels (`inv17_build_info`).

## 2. Version compatibility during rollout

4.3.0 supports interface version 1 only (`control::SUPPORTED_VERSIONS`), same as 4.2.0, so mixed fleets negotiate v1. Streams are instance-local, so no cross-instance state migrates.

## 3. Configuration rollout

Use `ConfigManager.activate(..., health_probe=...)` per instance; it swaps atomically and auto-rolls back on probe failure. Record `Provenance` (author, source_revision, digest).

## 4. Rollback

Triggers: any Sev0/Sev1; promotion criteria failed.
1. Stop promotion.
2. Redeploy previous package (4.2.0) on affected instances. Open streams on restarted instances are lost; clients reopen (spec/crash-semantics.md).
3. Config-only issue: `ConfigManager.rollback(author, reason)`.
4. If rollback itself is unsafe, `emergency_disable` (operations/emergency-disable.md).
