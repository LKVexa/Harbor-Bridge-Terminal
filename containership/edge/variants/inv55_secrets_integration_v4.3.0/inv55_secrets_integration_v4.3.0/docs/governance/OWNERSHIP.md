# Ownership and escalation

| ID | INV55-GOV-OWNERSHIP | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

No owners have been assigned. All fields are placeholders.

| Role | Assignee | Alternate |
|---|---|---|
| Service owner | `<UNASSIGNED: service-owner>` | `<UNASSIGNED: service-owner-alt>` |
| Security owner | `<UNASSIGNED: security-owner>` | `<UNASSIGNED: security-owner-alt>` |
| Operations owner | `<UNASSIGNED: operations-owner>` | `<UNASSIGNED: operations-owner-alt>` |
| Release manager | `<UNASSIGNED: release-manager>` | — |
| Key custodian | `<UNASSIGNED: key-custodian>` | — |
| Escalation alias | `<UNASSIGNED: escalation-alias>` | — |
| Paging route | `<UNASSIGNED: paging-route>` | — |
| Business-hours contact | `<UNASSIGNED>` | — |
| After-hours contact | `<UNASSIGNED>` | — |

## Escalation timers (proposed)
| Severity | Ack | Escalate to owner | Escalate to security |
|---|---|---|---|
| SEV1 (leak, audit break, key compromise) | 15 min | 30 min | immediately |
| SEV2 (provider outage, frozen) | 30 min | 2 h | if security-related |
| SEV3 | next business day | — | — |

Code ownership: `/CODEOWNERS`. Service metadata: `/catalog-info.yaml`.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
