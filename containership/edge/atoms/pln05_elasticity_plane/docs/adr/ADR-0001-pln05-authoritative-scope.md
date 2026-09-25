# ADR-0001 — PLN-05 authoritative scope

- **Status:** PROPOSED — awaiting approval by the accountable architecture owner (role `pln05.architecture-owner`, see `ops/oncall.json`). Until approved, MC-01 stays open and the exit gate is NO_GO.
- **Date:** 2026-09-23
- **Deciders (required):** architecture owner, service owner. **Recorded by:** chop-shop pass 4.2.0 (not an approver).
- **Supersedes (on approval):** CHECKLIST.json C010/C011 source-function wording (snapshot/restore, Dandelion-style microfunctions, HyperFlux-like reassignment) *as a statement of PLN-05 ownership*.

## Context

Two sources disagree. `CHECKLIST.json` C010/C011 names the source function as snapshot/restore, Dandelion-style microfunctions and HyperFlux-like resource reassignment. `contract.py`, the README, the implementation and every test since 4.0.0 define PLN-05 as a **hysteretic capacity-target controller** that explicitly does not own placement or provisioning. A checklist item cannot be satisfied by code that the contract forbids, and the contract cannot be silently rewritten from a checklist sentence.

## Responsibility matrix

| Responsibility | Class | Owner if not PLN-05 |
|---|---|---|
| demand observation | OBSERVE | GAP-09 supplies the signal |
| hysteresis | OWN | — |
| capacity target calculation | OWN | — |
| floor/ceiling enforcement | OWN | — |
| scale-to-zero decision | OWN | — |
| placement | OUT_OF_SCOPE | SCH-01 |
| provisioning | OUT_OF_SCOPE | node/provider layer |
| resource reassignment (HyperFlux-style) | OUT_OF_SCOPE | SCH-01 / provider adapters |
| snapshot | OUT_OF_SCOPE | INV-26 MicroVM snapshotting |
| restore | OUT_OF_SCOPE | INV-26 (cold-start mitigation); PLN-05 only *consumes* restore latency as an input to its grace model |
| microfunction lifecycle (Dandelion-style) | OUT_OF_SCOPE | execution tier (INV-31 function execution) |
| failover of controller ownership | OWN | — |
| execution ownership | OUT_OF_SCOPE | execution tiers |

The machine-readable copy is `spec/pln05_scope.json`, generated from `spec.py`; `tools/check_repo.py` fails CI if README, scope file, contract source or traceability disagree.

## Decision (proposed)

1. PLN-05 **SHALL** own capacity targets per workload: convert observed demand into a bounded, hysteretic scale decision including scale-to-zero.
2. PLN-05 **SHALL NOT** emit a target outside the active `[floor, ceiling]` envelope, place capacity, provision nodes, take or restore snapshots, run microfunctions, or reassign resources.
3. C010/C011 are re-read as: *"approve an ADR for PLN-05 and translate its capacity-control function into SHALL-level requirements"*. The snapshot/microfunction/reassignment wording is recorded as belonging to the sibling elements named above.

### Source-of-truth precedence

ADR (accepted) → `spec.py` / `spec/*.json` → `schemas/*.json` → code → tests → README → CHECKLIST requirement prose.

## Alternatives considered

- **A. Expand PLN-05 to own snapshot/restore, microfunctions and reassignment.** Rejected: contradicts every shipped contract and test, duplicates INV-26/INV-31/SCH-01 ownership, and would require an owning API, durability model, isolation boundary, provider authority and fencing for three new subsystems with no sibling agreement.
- **B. Leave the contradiction unresolved.** Rejected: the audit's P0 blocker; scope drift cannot be tested.
- **C. (Chosen, pending approval)** Capacity-controller-only, with the three functions attributed to siblings.

## Consequences

- No sibling contract version changes: the three interfaces stay `/1`.
- Architecture invariants future changes may not violate: no ambient filesystem/network/device authority in the decision path; demand is input, never authority; only `limits.update` (intent plane) sets the envelope; `ceiling.lower` is monotonic; publication requires a valid lease.
- Deprecation note: the retired interpretation had no implementation, so nothing is migrated; the CHECKLIST text is kept verbatim and annotated in `traceability/requirements.json` (C010/C011 status `superseded-proposed`).

## Open questions (owner input required)

- Confirm C (or choose A) — this is the approval that closes MC-01.
- Confirm INV-26 as the owner of restore-latency data and the contract PLN-05 consumes it through.
