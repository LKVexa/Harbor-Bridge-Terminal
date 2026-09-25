# GAP-08 owners and escalation (component 40)

**Status: UNASSIGNED.** No names were supplied with the candidate, and this pass does not invent them. Every row below must be filled by the accountable organisation before any production waiver or sign-off is valid.

| Role | Name | Contact / rotation | Backup | Review cadence |
|---|---|---|---|---|
| Service owner (GAP-08) | _unassigned_ | | | quarterly |
| Architecture owner (approves ADRs) | _unassigned_ | | | per ADR |
| On-call rotation (operational escalation) | _unassigned_ | | | weekly handoff |
| Security owner (integrity, keys, forged evidence) | _unassigned_ | | | quarterly |
| Release manager (evidence bundle, SBOM, signing) | _unassigned_ | | | per release |
| Vulnerability response owner | _unassigned_ | | | monthly triage |
| Waiver approver (P0/P1 risk acceptance) | _unassigned_ | | | on request |

## Incident severity model (proposed)

| Sev | Definition | Response |
|---|---|---|
| 1 | Bad bundle beyond first wave; rollback incomplete on > 1 node; integrity failure; forged ack/evidence accepted | page on-call + security owner immediately; global freeze |
| 2 | Rollback incomplete on 1 node; controller cannot roll back (dependency) | page on-call |
| 3 | Deferred nodes escalated; drift detected; evidence rejected repeatedly | ticket, next business day |

## Waiver process

A waiver names: requirement id (section + item), risk, compensating control, owner, **expiry date ≤ 90 days**, approver ≠ requester. P0 waivers without owner and expiry are invalid. Waivers are recorded in `CHECKLIST_STATUS.md` → *Waivers* and in the release evidence bundle.
