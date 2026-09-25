# INV-67 ownership and escalation model

**Checklist item:** 01 (C009) · **Status:** role model implemented; **named people are a human input and are NOT filled in** (see blocker EXC-001 in `docs/governance/exceptions.json`).

Roles are defined so nothing depends on tribal knowledge. The machine-readable copy is `docs/governance/ownership.json`; the release evidence bundle embeds it, so every deployed artifact traces back to an accountable role.

| Role | Responsibility | Holder |
|---|---|---|
| Primary owner (INV-67 team) | translator, controller, CRD, release | _unassigned — required before release_ |
| Secondary owner | backup for all primary duties | _unassigned_ |
| Platform/Kubernetes reviewer | CRD/RBAC/deployment changes, cluster compatibility | _unassigned_ |
| Security reviewer | threat model, authn/z, artifact trust, exceptions | _unassigned_ |
| SRE/Operations | runbooks, alerts, on-call, game days | _unassigned_ |
| Downstream owner (SCH-01 / INV-68) | placement protocol `PK_K8S_PLACE/1` | _unassigned_ |
| Release authority | final exit gate sign-off | _unassigned_ |

## Responsibility boundaries

* **Translator (`translator.py`)** — INV-67 primary owner. Untrusted-input boundary; any change needs security review (CODEOWNERS).
* **Controller/CRD/RBAC (`plane/`, `api/`, `deploy/`)** — INV-67 primary owner + platform reviewer.
* **Placement/runtime** — SCH-01/INV-68 own placement decisions and runtime execution; INV-67 owns only the envelope and fencing/idempotency obligations it sends.
* **Security approval** — security reviewer for schema, RBAC, artifact-trust, and exception changes.
* **Release authority** — only role that may flip the exit gate to PASS.

## Approval rights

| Change | Approver(s) |
|---|---|
| Compatibility matrix / CRD version | primary owner + platform reviewer |
| Wire/JSON schema change | primary owner + downstream owner |
| Security exception / waiver | security reviewer (time-bounded, recorded in exceptions ledger) |
| Rollback | primary owner **or** on-call SRE (no second approval needed during an incident) |
| Emergency disable (freeze/quarantine) | any on-call SRE or security reviewer; audited automatically |

## Operational coverage and escalation

1. Alert fires (see `docs/telemetry/alerts.yaml`) → on-call SRE acknowledges within **15 min (P1)** / **4 h (P2)**.
2. If the failure class is owned downstream (runtime, scheduler) per `docs/architecture/LIFECYCLE.md#failure-ownership`, escalate to the downstream owner within 30 min.
3. Suspected compromise or cross-tenant action → security reviewer immediately; freeze first (`docs/runbooks/emergency-freeze.md`).
4. Unresolved after 2 h at P1 → release authority / platform leadership.

## Ownership transfer

Transfer is complete only when the receiving owner has signed a record containing: open-risk review, the current exceptions ledger, pending incidents, RBAC/credential transfer (rotate any personal credentials), CODEOWNERS update, and on-call rotation update. The record is appended to the audit trail with `action=ownership.transfer`.
