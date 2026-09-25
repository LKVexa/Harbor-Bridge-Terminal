# Ownership, escalation and governance (component 20) — BLOCKED

Names cannot be invented by the implementer; every role below must be filled by the organisation.

| Role | Primary | Delegate |
|---|---|---|
| Accountable service owner | UNASSIGNED | UNASSIGNED |
| Technical maintainer / code owner | UNASSIGNED | UNASSIGNED |
| Security owner / reviewer | UNASSIGNED | UNASSIGNED |
| SRE / operations owner | UNASSIGNED | UNASSIGNED |
| Release approver | UNASSIGNED | UNASSIGNED |
| pk_core dependency contact | UNASSIGNED | — |
| TLS / transport layer contact | UNASSIGNED | — |

Escalation ladder (proposed): on-call (15 min ack SEV1) → service owner (30 min) → security owner for any
policy bypass (immediately) → emergency change authority: service owner + security owner jointly.
ADRs 0001–0004 are **Proposed**; approval records go here with reviewer names and dates.
Waivers: `waivers.json` (machine-read by `evidence_gate`; ownerless or expired waivers are invalid).
Reviews (proposed cadence): architecture quarterly, access/capability monthly, supply chain per release,
config/policy per change, threat model per minor release.
