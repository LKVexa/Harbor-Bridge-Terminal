# Incident response plan (item 48; C097)

**Paging target:** UNASSIGNED — the plan cannot page anyone until `governance/OWNERS.json` names an on-call rotation. This is the blocker for item 48.

## Severity model
| SEV | Definition (INV-43 specific) | Response |
|---|---|---|
| SEV-1 | Evidence that a cross-tenant co-location was **permitted** without the required mitigations (a false permit), or audit chain verification fails | page immediately; freeze placement; preserve evidence |
| SEV-2 | `attack_suspected` refusals from a collector key; `internal_error` in decisions; new transient-execution CVE affecting fleet CPUs | page within 30 min; quarantine affected nodes |
| SEV-3 | Collector stalls, stale posture on > 5% of nodes, rollout auto-rollback | business hours |
| SEV-4 | Single-node posture absence, dashboard gaps | ticket |

## Containment
1. `POST /v1/control/freeze` (global) or `/v1/control/quarantine` per node.
2. Revoke suspect collector keys (`KeyRegistry.revoke`).
3. For a new CVE: add the mitigation to the policy baseline or class extras via rollout — unknown mitigations already fail closed, so the policy change *causes* refusals on unmitigated nodes, which is intended.

## Recovery
Re-enrol keys, re-attest nodes, `unfreeze`, verify `inv43_refusals_total` returns to baseline.

## Post-incident evidence
Archive: audit file + anchored head, explain records for affected `decision_id`s, `evidence/` bundle of the running release, config/policy digests, timeline. Record under `governance/reviews/` with an incident id.
