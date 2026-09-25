# Rollout and rollback

| ID | INV55-OPS-ROLLOUT | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Pre-rollout gate: CI (`.github/workflows/ci.yml` jobs `test`, `vault-real`, `secret-scan`, `gate`) and `tools/exit_gate.py` MUST report GO.

Plan (manual; automation NOT IMPLEMENTED beyond config rollback):

| Stage | Traffic | Gate to proceed |
|---|---|---|
| 0 Canary | 1 instance, canary workloads | 30 min: no `inv55_audit_failures_total` increase; `inv55_requests_total{outcome="terminal"}` rate not above baseline; p99 within performance-policy.md |
| 1 | 10 % | 1 h same gates |
| 2 | 50 % | 1 h |
| 3 | 100 % | — |

Rollback:
- Config: `ConfigController.rollback(steps)` (implemented; appends a `rollback` provenance layer).
- Code: redeploy previous package; leases are lost (clients re-resolve); scopes/retirements reload from the state file; audit chain resumes (`resume_from_file`).
- Automated canary analysis, traffic shifting: NOT IMPLEMENTED.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | CI/exit gate; state and audit continuity |
