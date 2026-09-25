# INV-72 ownership (C009)

Machine-readable source: `ops/OWNERS.json` (roles, RACI, ownership-change rule). Enforcement:
`.github/CODEOWNERS` and `tools/governance_check.py`.

**Status: BLOCKED.** Every role — service owner, security owner, release approver, on-call and the
architecture board — is `UNASSIGNED`. Nobody in this archive can name them, and a placeholder is
treated as a failure, not a pass. Until the holders are named:

* `tools/governance_check.py` exits 1,
* `tools/release_gate.py` returns NO_GO,
* the escalation tabletop in `ops/ESCALATION.json` stays NOT_RUN.

Rules the governance check enforces once names exist: no service/bot identity may hold a role; the
security owner and release approver must differ; README, SECURITY and RUNBOOK must link this file;
CODEOWNERS must cover every security-sensitive path.
