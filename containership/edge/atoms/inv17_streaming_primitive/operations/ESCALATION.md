# INV-17 Escalation

**Controls:** C009, C097 (checklist §1, §58).

All contacts are placeholders. No person has been assigned or has accepted these roles. Machine-readable record: governance/OWNERS.json.

## 1. Roles

| Role | Holder | Contact | Backup |
|------|--------|---------|--------|
| Accountable owner | UNASSIGNED — owner to fill | UNASSIGNED | UNASSIGNED |
| Primary on-call (holds `sre-oncall` admin principal) | UNASSIGNED — owner to fill | UNASSIGNED | UNASSIGNED |
| Security contact | UNASSIGNED — owner to fill | UNASSIGNED | UNASSIGNED |
| Incident commander (Sev0/1) | UNASSIGNED — owner to fill | UNASSIGNED | – |

The default admin principal allowed to run emergency controls is `sre-oncall` (`control::StreamRegistry(admins=("sre-oncall",))`); deployments should configure real principals.

## 2. Path

| Severity (see SEVERITY_MATRIX.md) | Page | Escalate if unacknowledged | Then |
|------------------------------------|------|---------------------------|------|
| Sev0 | Primary on-call immediately | 5 min (PROPOSED) → backup | Incident commander + owner |
| Sev1 | Primary on-call | 15 min (PROPOSED) → backup | Owner |
| Sev2 | Ticket + on-call notification | next business day | Owner |
| Sev3 | Ticket | – | – |

Security incidents (auth bypass, token replay, audit chain break from `AuditLedger.verify`) additionally go to the security contact at any severity.

## 3. Handover data

Attach: `/explain` and `/readyz` output, `/metrics` snapshot, `AuditLedger.export_jsonl()` excerpt with `anchor()`, config `ConfigManager.provenance`.
