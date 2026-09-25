# Ownership, Escalation and Approvals (C47)

**Status: BLOCKED — named people must be assigned by the organization.** No names are invented here. Every Exit record in the checklist carries these same blanks.

| Role | Responsibility | Assignee | Backup |
|---|---|---|---|
| Accountable owner (GAP-04) | GO/NO-GO, invariants, contract changes | ________ | ________ |
| Security owner | crypto, trust bundles, threat model, vuln response | ________ | ________ |
| SRE / operations owner | runbooks, alerts, on-call, backups | ________ | ________ |
| Release engineering | build, signing key custody, SBOM | ________ | ________ |
| Policy owner (GAP-13 liaison) | policy semantics | ________ | ________ |
| Adjacent owners | GAP-01, GAP-05, GAP-12, PLN-07 contracts | ________ | ________ |

## RACI
| Activity | Accountable | Responsible | Consulted | Informed |
|---|---|---|---|---|
| Change to safety invariant / schema | Accountable owner | Engineer | Security, adjacent owners | SRE |
| Trust bundle / key rotation | Security owner | Release eng. | Accountable owner | SRE |
| Production override / quarantine release | SRE owner | On-call | Security | Accountable owner |
| Release GO | Accountable owner | Release eng. | Security, SRE | Product |

Escalation: on-call → owner (15 min for SEV1) → accountable owner's manager (30 min). Support: 24×7 for SEV1/SEV2 (service is safety-critical at the edge). Owner changes require a handoff record; ownership reviewed quarterly and on reorganization. `CODEOWNERS` must list the owners above once assigned.
