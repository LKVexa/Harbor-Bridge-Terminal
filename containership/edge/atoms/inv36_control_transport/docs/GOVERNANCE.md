# Governance, ownership and production exit (MC-21)

**Status: proposed.** All named roles are UNASSIGNED; gate check G10 fails until the repository owner assigns them in `governance/owners.json` and selects a license.

## Ownership and RACI

Roles: service owner (A), technical owner, security owner, release owner, on-call primary, performance owner, legal contact - defined in `governance/owners.json` (versioned in the repository; mirror into the service catalog).

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Code/protocol changes | technical owner | service owner | security owner | on-call |
| Crypto / handshake / key changes | technical owner | security owner | service owner | release owner |
| Policy, wildcard, break-glass rules | security owner | security owner | technical owner | service owner |
| Config changes | on-call / release owner | service owner | technical owner | - |
| Deployment / rollback | release owner | service owner | on-call | tenants (SEV1/2) |
| Incident response | on-call | service owner | security owner (security incidents) | stakeholders |
| Deprecation | technical owner | service owner | release owner | consumers |

Support: 24x7 for SEV1/SEV2, business hours for SEV3/SEV4.

## SLOs and error budgets (proposed)

| SLO | Objective | Window | Budget exhausted => |
|---|---|---|---|
| Authenticity | 0 unauthenticated frames acted upon | always | immediate SEV1 |
| Relay blindness | 0 plaintext bytes visible to relays | always | immediate SEV1 |
| Availability (per host/guest pair) | 99.95 % | 30 days rolling | freeze non-security releases; postmortem |
| Control latency | p99 seal+open <= 50 us (certified target); p99 control op <= 25 ms | 7 days | performance review; regression waiver needed to ship |

## Incident severity

| Sev | Examples | Response |
|---|---|---|
| SEV1 | authentication bypass; cross-tenant exposure; key compromise; plaintext exposure | page on-call + security owner immediately; incident commander; quarantine/kill switch considered; comms within 1 h |
| SEV2 | fleet-wide transport outage; replay/integrity attack in progress; CRITICAL traffic shed; dependency compromise suspected | page on-call; security owner if attack class; mitigation within 1 h |
| SEV3 | widespread latency degradation; policy misconfiguration; single-node outage | ticket + on-call during hours |
| SEV4 | telemetry drops; informational load | backlog |

Process: page -> incident commander -> containment (quarantine per `docs/RUNBOOKS.md`) -> evidence preservation (RUNBOOKS "Forensics") -> recovery -> blameless postmortem within 5 business days -> regression test added.

Quarantine criteria: any SEV1 affecting a scope; attack-class SEV2 with an identified source. Global emergency disable: only SEV1 with confirmed ongoing compromise, two approvers, `confirm_global`.

## Vulnerability response and lifecycle

- Intake: security contact (UNASSIGNED) -> triage within 2 business days -> embargo if exploitable -> fix -> verification (regression test + gate) -> coordinated disclosure -> operator notice.
- Patch SLAs: critical 72 h; high 7 days; medium 30 days; low next scheduled release. Exploited-in-the-wild critical: emergency release + quarantine guidance.
- Supported branches: current minor (5.1.x) and previous minor (5.0.x) of the current major; each minor supported 12 months after its successor ships (EOL dates published per release in CHANGELOG).
- Protocol deprecation notice: >= 90 days / two minor releases (see `docs/PROTOCOL.md`) unless emergency security action.
- Dependency updates: monthly routine; security updates per SLA.

## Recurring reviews

| Review | Cadence |
|---|---|
| Access (who holds identity/quarantine/signing keys, CI environments) | quarterly |
| Keys (rotation status, epochs, revocations) | monthly |
| Policy (rules, wildcards, break-glass grants) | quarterly |
| Dependencies (pip-audit trend, versions) | monthly |
| Configuration (drift vs golden profiles) | quarterly |
| Threat model + ADR | yearly or on ADR re-review trigger |
| Compatibility matrix | each minor release |

## Exceptions, waivers, debt

`governance/waivers.json` (scope, justification, compensating controls, risk owner, approver, expiry; `proposed` waivers carry no authority) - expired waivers fail G10 automatically, and an expired waiver requires remediation or re-approval before release. `governance/debt.json` tracks technical debt and deprecated behaviours with target releases.

## Production exit gate

Machine-readable checklist: `release/exit-gate.json` (architecture, requirements, interfaces, implementation, security, resilience, performance, observability, tests, compatibility, rollback, operations, ownership, license, SBOM/provenance, gate evidence). Rules: every mandatory item PASS; SKIP/ERROR are non-passing unless an *approved* waiver applies; the gate result is bound to source and artifact digests; named approvers (service, technical, security, release owners) sign the decision record; the complete evidence bundle is archived immutably (CI artifact retention 400 days + WORM copy).
