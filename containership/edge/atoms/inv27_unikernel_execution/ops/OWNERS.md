# INV-27 owners and escalation (MC-012; C009)

Roles and the escalation chain are machine-readable in `ops/OWNERS.json`. **Every holder is
`UNASSIGNED`**, so `tools/governance_check.py` fails and the release gate stays NO_GO until the
owner names people (W-OWNERS).

Separation of duties: the release approver must differ from the security owner, and no role may be
held by a service identity (bot, ci, automation, claude).

| Role | Duty |
|---|---|
| inv27-service-owner | accountable for behaviour, this repository and waivers |
| inv27-security-owner | seal/trust/isolation decisions, vulnerability response (SECURITY.md) |
| inv27-release-approver | signs the release gate |
| inv27-oncall | first responder (ops/INCIDENT.md) |
| inv27-architecture-reviewer | ADRs and interface changes |
