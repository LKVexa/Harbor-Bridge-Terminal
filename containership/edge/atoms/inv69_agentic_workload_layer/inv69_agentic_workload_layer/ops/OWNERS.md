# INV-69 ownership, RACI and escalation (C009)

Machine-readable twin: `ops/OWNERS.json` (checked by `tools/governance_check.py`, which **fails** while any
required holder is `UNASSIGNED`). Role aliases are stable; people behind them change through the transfer
process below.

## Accountable owner

| Role alias | Holder | Backup | Status |
|---|---|---|---|
| `inv69-service-owner` (single accountable owner) | UNASSIGNED | UNASSIGNED | **open — must be named by the owner of this repository** |
| `inv69-security-owner` (trust policy, signer keys, waivers of security class) | UNASSIGNED | UNASSIGNED | open |
| `inv69-release-approver` (signs `--approval` for `tools/release_gate.py`) | UNASSIGNED | UNASSIGNED | open |
| `inv69-oncall` (L1 operations pager) | UNASSIGNED | — | open |
| `pk-architecture-board` (L3 architecture decisions) | UNASSIGNED | — | open |

No person or automation was named in the supplied candidate or checklist, so none is invented here.
A holder naming a service identity (bot/ci/automation/pipeline/claude) is refused by the release gate.

## RACI

| Activity | R | A | C | I |
|---|---|---|---|---|
| Product ownership / scope | service-owner | service-owner | architecture-board | oncall |
| Runtime operations | oncall | service-owner | security-owner | architecture-board |
| Security response | security-owner | security-owner | service-owner | release-approver |
| Dependency management | service-owner | service-owner | security-owner | oncall |
| Release approval | release-approver | service-owner | security-owner | oncall |
| Data-governance / telemetry policy | security-owner | service-owner | architecture-board | oncall |

Separation of duties: `inv69-security-owner` and `inv69-release-approver` must be different people
(checked by `tools/governance_check.py`).

## Escalation (tiered)

L1 `inv69-oncall` → L2 `inv69-service-owner` → L3 `inv69-security-owner` (security) / `pk-architecture-board`
(architecture). Per incident class and severity: `ops/ESCALATION.json`. Procedures: `ops/RUNBOOK.md`.

Coverage: **24x7** for SEV1/SEV2 (after-hours pager held by `inv69-oncall`); business hours for SEV3/SEV4.
Emergency containment (`GovernedRuntime.contain`) may be authorised by `inv69-oncall` alone and must be
reviewed by `inv69-service-owner` within one business day.

## Transfer and revalidation

- Ownership changes are a pull request to `ops/OWNERS.json` + this file, reviewed per `.github/CODEOWNERS`.
- Owners are revalidated quarterly in the access review (`ops/REVIEWS.json`, review `R-ACCESS`).
