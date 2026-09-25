# Ownership, escalation and RACI (MC-001) — UNBOUND

No accountable people or aliases were supplied with this archive, and inventing them would be false
evidence. Every role below is **UNBOUND**; `tools/exit_gate.py` reports NO_GO until each has a durable alias.

| Role | Alias | Backup |
|---|---|---|
| Accountable service owner | UNBOUND | UNBOUND |
| Owning team | UNBOUND | — |
| Technical lead | UNBOUND | UNBOUND |
| Architecture approver | UNBOUND | — |
| Operations owner / on-call rotation | UNBOUND | UNBOUND |
| Security reviewer | UNBOUND | — |
| Release approver | UNBOUND | — |

## Escalation
L1 on-call (ack per `INCIDENT_RESPONSE.md`) → L2 owning team lead (after 30 min SEV1/SEV2 or on any
split-brain/security signal) → L3 architecture/security owners + incident commander. Mandatory escalation to
security on A-ATK-1 or audit verification failure; to network on multi-site partition; to platform on
wasmCloud host faults.

## RACI
| Area | R | A | C | I |
|---|---|---|---|---|
| Topology schema & wire contracts | tech lead | service owner | GAP-02/03/04/12 owners | ops |
| Routing policy & precedence | tech lead | service owner | security | schedulers |
| Coordinator election | tech lead | architecture approver | GAP-04 owner | ops |
| Configuration | ops owner | service owner | security | tech lead |
| Security policy & keys | security reviewer | service owner | ops | all |
| Releases | tech lead | release approver | security, ops | consumers |
| Incident response | on-call | ops owner | security | stakeholders |
| Production rollback | on-call | ops owner | tech lead | stakeholders |

Ownership transfer: update this file and `CODEOWNERS` in one reviewed change; previous owners stay in git
history; the exit record names owners at release time.
