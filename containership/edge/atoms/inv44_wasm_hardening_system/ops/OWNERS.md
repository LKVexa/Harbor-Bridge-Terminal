# Ownership and escalation — INV-44 (C009)

| Role | Holder | Escalation | Status |
|---|---|---|---|
| Accountable owner | UNASSIGNED | — | open |
| Security owner (approves verifier keys, toolchain allowlist) | UNASSIGNED | — | open |
| Release approver (signs `--approval` for release_gate) | UNASSIGNED | — | open |
| On-call (pages from ops/alerts.yaml) | UNASSIGNED | — | open |
| Config activator (`ConfigStore.activate`) | UNASSIGNED | — | open |

Rules the code already enforces for whoever is named:
- A release approval naming a service identity (bot/ci/service/automation/pipeline/claude) is refused by `release_gate.evaluate`.
- A `Principal` can only come from an `Authenticator`; service principals are marked.
- The same person should not hold both *Security owner* and *Release approver* (separation of duties — policy, not yet code).
