# Runbook: Day-1 Deploy (release of INV-63 and first workloads)

| Field | Value |
|---|---|
| Document ID | INV63-RB-DAY1 |
| INV-63 C-IDs covered | C096, C092 |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role), Release approver (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change. |

## A. Release gate (before installing a new INV-63 version)
1. `python -m unittest discover -s tests` — green.
2. `python perf/bench.py --gate` — exit 0 (`gate_failures: []`). Thresholds are PROPOSED; re-baseline on approved hardware.
3. `python audit.py [--out-dir evidence]` — regenerates evidence and traceability.
4. `python gate.py [--out release/GATE_RESULT.json]` — evaluates `release/GATE_POLICY.json` G-01..G-10 (tests, audit, perf, pins, owners, waivers, reviews, evidence freshness, pk_core conformance, signature). Criterion statuses PASS/FAIL/BLOCKED/SKIPPED/NOT_RUN/WAIVED. Verdict: any FAIL → NO_GO; any mandatory BLOCKED/SKIPPED/NOT_RUN → BLOCKED; any WAIVED → CONDITIONAL_GO; else GO. GO needs an Ed25519 signature from `INV63_GATE_SIGNING_KEY` (env:/file: ref to a hex seed). Exit 0 only for GO/CONDITIONAL_GO. Expected today: BLOCKED (pins unapproved, Wadm/pk_core UNPINNED, owner roles UNASSIGNED).
5. Record release id (`inv63-4.3.0` default in `DeploymentService.release`), config digest, schema digests (`fixtures/FIXTURES.json`).

## B. Install / upgrade the manager instance
1. Take a backup (`BACKUP_RESTORE.md`).
2. Stop the old process; start the new one on the same `state_dir`. `_recover` replays the journal. Only one process may write: a second handle gets `INV63-E-STALE-EPOCH` / `INV63-E-CONFLICT`.
3. Verify `status()`: `ready`, `leader`, `version == "4.3.0"`, `dependencies.lattice == "up"`, `breaker == "closed"`.

## C. Onboard a workload (tenant principal with role `tenant-deployer`)
1. Send `set_desired` with body `PK_DEPLOY_DESIRED/2` (signed `artifact`: `digest`, `key_id` in the verifier's trusted keys, `signature`). v1 is rejected in prod (`INV63-E-ARTIFACT-UNTRUSTED`).
2. Expect `outcome: SUCCESS`, `result.state: VALIDATED`.
3. Send `reconcile` `{tenant, component}`; expect `SUCCESS` with `started == count`. A second `reconcile` must return `started: 0, stopped: 0` (convergence).
4. `explain` `{tenant, component}` — confirm `accept_desired` and `reconcile` decisions and policies (`signed-artifact`, `tenant-quota`, `residency`, `spread`).
5. Every request needs a unique `idempotency_key`; reuse with a different body → `INV63-E-CONFLICT`.

## D. Version changes
Use `CANARY_ROLLBACK.md`.

Last exercised: NEVER — game day required
