# INV-08 RACI and escalation map

Machine-readable source: `production/ownership.json` (loader `production/ownership.py`,
`python -m inv08_dynamic_infrastructure_model.production.ownership [role]`).
**Every person, rotation and contact is UNASSIGNED.** The loader reports each as a
production blocker; nothing here names a real person.

| Role | Design | Release | Operate | Security |
|---|---|---|---|---|
| service_owner | A | A | C | C |
| platform_owner | C | R | A | I |
| security_owner | C | C | I | A |
| oncall_primary / oncall_secondary | I | I | R | I |
| incident_commander | I | I | R | R |
| security_escalation | I | C | C | R |

- Operational escalation: oncall_primary -> oncall_secondary -> incident_commander -> service_owner.
- Security escalation: security_escalation -> security_owner -> incident_commander.
- Vendor/provider handoff: no provider integration exists; rule: incident_commander opens a vendor case for SEV2+ attributed to a provider, mitigation ownership stays with oncall_primary.
- Validation: exactly one Accountable per activity; chains reference defined roles.
