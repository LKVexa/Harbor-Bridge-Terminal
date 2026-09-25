# INV-71 ownership, authority and escalation (C009)

**Status:** TEMPLATE WITH UNASSIGNED ROLES. No person or team has accepted any role below. The remediation pass does not name owners on anyone's behalf; the production gate (`tools/production_gate.py`) fails while any role is `UNASSIGNED` in `governance/raci.json`.

## Roles

| Role | Accountable for | Assigned to | Secondary |
|---|---|---|---|
| Service owner | INV-71 product/service outcome, final production acceptance (FINAL-10) | UNASSIGNED | UNASSIGNED |
| MicroVM runtime owner | Firecracker/jailer versions, guest kernel/rootfs, snapshot pipeline | UNASSIGNED | UNASSIGNED |
| Host-platform owner | host kernel baseline, KVM, cgroup v2, node bootstrap and qualification | UNASSIGNED | UNASSIGNED |
| Network/security owner | egress policy, DNS enforcement, seccomp/device policy, signing roots, threat model | UNASSIGNED | UNASSIGNED |
| SRE / on-call owner | SLOs, alerts, runbooks, capacity, rollback drills | UNASSIGNED | UNASSIGNED |
| Release authority | promotion of an exact release digest; separate from build authority | UNASSIGNED | UNASSIGNED |
| Incident commander (rotation) | SEV1/SEV2 command, containment decisions | UNASSIGNED | UNASSIGNED |
| pk_core interface owner | the external conformance dependency (INV71-X001) | UNASSIGNED | UNASSIGNED |

## RACI for security-critical actions

Enforced in code by `control/auth.py` (`ROLES`, `TWO_PERSON`); rendered in `docs/generated/AUTHZ.md`. R = performs, A = accountable, C = consulted, I = informed.

| Action | Workload/scheduler | Operator-contain | Policy editor | Release manager | Break-glass | Security owner | Service owner |
|---|---|---|---|---|---|---|---|
| create / stop / teardown | R | I | - | - | - | - | A |
| egress policy update (two-person) | - | - | R | - | - | A | I |
| config activation (two-person) | - | - | R | - | - | C | A |
| freeze / quarantine session or node | - | R | - | - | R | I | A |
| emergency disable | - | R | - | - | R | I | A |
| emergency re-enable (two-person) | - | - | - | - | R + second approver | C | A |
| artifact promotion (two-person) | - | - | - | R | - | C | A |
| rollback (two-person) | - | - | - | R | R | I | A |

No single role can both approve and bypass a security control: every two-person action requires a second, distinct principal holding the same action, and self-approval is denied (`AUTHZ.SELF_APPROVAL`). Host capabilities (`host.kvm.open`, `host.tap.create`, `host.cgroup.write`, `host.overlay.mount`) belong only to the `node-helper` identity.

## Authority boundaries

| Change | Who may make it | Review required |
|---|---|---|
| Firecracker / jailer / guest kernel / rootfs pins | runtime owner via signed manifest (`artifacts/approved-manifest.json`) | security owner + release authority |
| Network (egress) policy | policy editor, two-person | security owner |
| Seccomp / device policy | runtime owner | security owner; ADR supersession if the confinement model changes |
| Resource ceilings | SRE owner | service owner |
| Signing roots / trust anchors | security owner | service owner + release authority |
| Production rollout state | release authority | SRE owner |

## Escalation (to be filled by the owners)

| Step | Target | Acknowledge within | Then |
|---|---|---|---|
| 1 | primary on-call (UNASSIGNED paging target) | 5 min for SEV1, 15 min for SEV2 (PROPOSED) | step 2 |
| 2 | secondary on-call (UNASSIGNED) | 10 min | step 3 |
| 3 | incident commander + service owner (UNASSIGNED) | 15 min | vendor/security escalation |
| Break-glass | two break-glass holders; use is audited `EMERGENCY.*` and reviewed within 1 business day | - | - |

## Not done here (BLOCKED on people)

- Named owners, paging targets and vendor contacts.
- The ownership/paging drill (C009-IMP-05): it needs a real paging system and people to page.
