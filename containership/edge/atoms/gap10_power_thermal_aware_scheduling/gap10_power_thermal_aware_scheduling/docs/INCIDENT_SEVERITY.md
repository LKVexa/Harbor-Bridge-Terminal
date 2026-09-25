# GAP-10 Incident Severity, Paging and Escalation (component 39)

| Severity | Definition | Examples (alert) | Paging | Ack / escalate |
|---|---|---|---|---|
| **SEV1** | A placement ceiling is not being enforced, or fleet-wide capacity loss | `Gap10EnforcementDivergence`, `Gap10FleetWideDerating` | Page GAP-10 on-call **and** scheduler on-call immediately | Ack 5 min; escalate to engineering owner at 15 min, incident commander at 30 min |
| **SEV2** | Safety evidence compromised or a physical/cooling emergency in progress | `Gap10ForgedInput`, `Gap10CoolingDomainFailure`, `Gap10BatteryEmergency`, `Gap10NotSafeToEnforce` | Page GAP-10 on-call; notify security for forged input, facilities for cooling | Ack 15 min; escalate at 30 min |
| **SEV3** | Degraded but fail-closed operation | `Gap10TelemetryStale`, `Gap10NodeExcluded`, `Gap10DependencyFailures`, `Gap10DecisionLatency` | Ticket + business-hours page | Ack 4 h |
| **SEV4** | Informational | `Gap10NodeDerated`, `Gap10ControlsActive` | Dashboard only | Weekly review |

Rules:

- A fail-closed state (capacity lost, safety kept) is never downgraded to "no incident" just because it is safe; capacity loss is tracked at SEV3 or higher.
- Security events (forged input) always open a security ticket regardless of impact.
- Post-incident: every SEV1/SEV2 requires a review with the audit chain verified and attached.
- On-call rotations and names are assigned in `docs/OWNERSHIP.md` (currently open, EX-001).
