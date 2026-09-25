# Runbook: Canary, Staged Rollout and Rollback

| Field | Value |
|---|---|
| Document ID | INV63-RB-CANARY |
| INV-63 C-IDs covered | C038, C092 |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role), Release approver (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change. |

## Workload version rollout (`op_rollout`, role `tenant-deployer`, capability `rollout:run`)
1. Pre-checks: `status().dependencies.lattice == "up"` (rollouts are refused offline: `INV63-E-CONTROL-PLANE-OFFLINE`); workload not frozen/quarantined; lifecycle `CONVERGED` or `VALIDATED` (from `DEGRADED` it fails `INV63-E-ILLEGAL-TRANSITION`).
2. Stage the environments: dev → staging → prod, one site at a time (edge sites last). This ordering is procedural, not enforced by code.
3. Send `rollout` with `PK_DEPLOY_ROLLOUT/1`: `{tenant, component, version, max_unavailable, canary, artifact}`. New version must pass `ArtifactVerifier` (`INV63-E-ARTIFACT-UNTRUSTED` otherwise).
4. Behaviour: first batch size = `canary` (if > 0), later batches = `max_unavailable`; each instance: stop old → start new → `adapter.healthy(new)`. Response `{batches, worst_unavailable}`; journal `rollout_batch` per batch; metric `rollout_batches`.
5. Verify: `explain` shows `rollout`; second `reconcile` is a no-op.

## Automatic rollback
Any error in a batch (start failure after retries, unhealthy instance, deadline) → lifecycle `ROLLING_BACK` → `_rollback` stops replaced new instances, restarts old ones, restarts unreplaced stopped ones → `CONVERGED` or `DEGRADED`. Response error `INV63-E-ROLLOUT-FAILED` with `{batch, cause, restored}`; decision `auto_rollback`; metric `rollbacks{kind="automatic"}`. Desired version stays the old one. If `_rollback` itself fails: lifecycle `FAILED`, `INV63-E-ROLLOUT-FAILED` with `details.state = "FAILED"`, `cause`, `rollback_error`; metric `rollbacks{kind="failed"}` — follow `INCIDENT.md`. Within a batch the old instance is stopped before the new one starts (DEBT-004); starts go through the circuit breaker.

## Operator rollback (`rollback` op, role `sre-operator`, capability `rollback:run`)
1. Send `rollback` `{tenant, component}`. The service finds the most recent `desired_set` with a different version (absent after `compact()`), checks controls (`INV63-E-FROZEN`/`INV63-E-QUARANTINED`), moves to `ROLLING_BACK`, keeps the current `count`, journals a new `desired_set`, then reconciles (`ROLLING_BACK → RECONCILING → CONVERGED`).
2. Result includes `rolled_back_to`; decision `operator_rollback`; metric `rollbacks{kind="operator"}`. `INV63-E-PRECONDITION` if no prior version exists.
3. Note: the artifact of the older version is not re-verified.

## Configuration rollback
`ConfigStore.rollback(author, reason)` then restart the service with the resulting config; record the new activation digest.

## Emergency disable
`svc.emergency_disable(True, principal)` (tenant `*`, `control:freeze`; else `INV63-E-FORBIDDEN`) → `set_desired`, `reconcile`, `rollout` and `rollback` raise `INV63-E-FROZEN` and `tick()` skips every workload (`explain` and freeze/quarantine ops remain available); `status().ready == false`. Re-enable with `emergency_disable(False, principal)`. Journaled and replayed across restart.

Tests: `tests/test_service.py::RolloutTest` (`test_canary_then_bounded_batches`, `test_failed_rollout_rolls_back_automatically`, `test_operator_rollback`, `test_rollout_requires_signed_new_version`), `ControlsTest::test_freeze_quarantine_and_emergency_disable` — all against `InMemoryLattice`; not exercised on a live lattice.

Last exercised: NEVER — game day required
