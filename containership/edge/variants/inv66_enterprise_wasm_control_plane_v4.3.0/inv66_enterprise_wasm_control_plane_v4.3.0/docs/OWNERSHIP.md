# INV-66 ownership and escalation matrix (MC-003, C009)

Document ID `INV66-OWN` · v1.0.0 · 2026-09-22 · reviewed quarterly (REVIEWS.md)

> **Status: roles defined, names pending.** Named individuals must be confirmed by the organisation before production; until then waiver **W-001** applies and the production exit gate (MC-068) cannot return GO.

| Role | Responsibility | Named holder | Backup |
|---|---|---|---|
| Accountable service owner | Scope, roadmap, release approval, waiver approval (Medium/Low) | *Proposed: David Paul Russell (LinearFinance.org Research Division) — to be confirmed* | *TBD* |
| Security owner | Threat model, key custody policy, security waivers (Critical/High), incident command for security events | *TBD* | *TBD* |
| Operations / on-call owner | Pager rotation, runbooks, capacity, backup/restore drills | *TBD* | *TBD* |
| Policy administrator(s) | Config revisions (two-person rule enforced in code for prod) | *TBD* | *TBD* |
| Auditor | Quarterly access & audit-chain review | *TBD* | — |

## Escalation route

1. On-call engineer (page: alert rules in `deploy/alerts.yaml`) — acknowledge ≤ 5 min (Sev1), ≤ 15 min (Sev2).
2. Operations owner — engaged at 15 min unresolved Sev1 or any data-integrity alert.
3. Security owner — engaged immediately for `Inv66AuditChainBroken`, `Inv66AnchorMismatch`, auth anomalies, or suspected compromise.
4. Service owner — decides freeze/unfreeze of an organisation and external communication.

Contact channels, rotation calendar and pager integration keys are organisation-specific and are recorded in the organisation's on-call system, not in this repository (no secrets or personal data in VCS).
