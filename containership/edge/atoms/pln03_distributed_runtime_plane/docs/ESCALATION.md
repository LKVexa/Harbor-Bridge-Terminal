# PLN-03 escalation path (MC-001.04–.05)

Contacts resolve through `OWNERS.yaml`; this file never carries personal phone numbers.

| Severity | Examples | Route (in order) | Ack target | Handoff rule |
|---|---|---|---|---|
| SEV1 | cross-tenant read, capability served without binding, audit chain break, data loss of an accepted publish | oncall_primary → accountable_owner → security_contact (parallel) | 5 min, 24×7 | Written handoff in incident channel; deputy assumes authority if owner unacknowledged at 30 min |
| SEV2 | site/region failure, breaker open on all adapters, sustained SLO burn > 10×, fencing conflict | oncall_primary → oncall_secondary → accountable_owner | 15 min, 24×7 | Handoff at shift change with open-action list |
| SEV3 | single adapter degraded, retry budget exhausted, degraded-mode buffering > 1 h | oncall_primary | 1 business hour | Ticket |
| Release-blocking | failed release gate, unresolved OWNERS, unsigned evidence | release_approver → accountable_owner | 1 business day | Ticket |

Security events (any SEV) additionally page `security_contact`. Data-integrity events additionally notify the PLN-06 counterpart. After-hours ownership follows the on-call rotation; the accountable owner remains accountable.
