# PLN-03 RACI (MC-001.03)

Roles are the slots in `OWNERS.yaml`; R = Responsible, A = Accountable, C = Consulted, I = Informed.

| Responsibility | Owner | Deputy | On-call | Security (PLN-07) | Arch board | Release approver | Adjacent planes |
|---|---|---|---|---|---|---|---|
| Runtime API surface (`plane.py`, `runtime.py`) | A | R | I | C | C | I | I |
| Adapter binding & lifecycle | A | R | R | C | I | I | C (INV-49) |
| Wire schemas / WIT (`schemas/`, `wit/`) | A | R | I | C | C | I | C (all) |
| Capability-token verification (`tokens.py`) | A | R | I | R | I | I | C (PLN-07) |
| Audit chain (`audit_log.py`) | A | R | I | R | I | I | I |
| Observability (`telemetry.py`) | A | R | R | I | I | I | I |
| Configuration activation / rollback | A | R | R | C | I | C | I |
| Deployment, canary, promotion | A | C | R | I | I | R | I |
| Rollback / emergency disable | A | R | R | C | I | I | I |
| Incident response | A | R | R | R (security events) | I | I | C |
| Architecture decisions (ADRs) | R | C | I | C | A | I | C |
| Release approval | C | C | I | C | I | A/R | I |
| Compatibility exceptions | R | C | I | C | A | C | C |
