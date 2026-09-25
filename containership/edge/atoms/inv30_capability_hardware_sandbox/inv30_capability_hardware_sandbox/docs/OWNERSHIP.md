# INV-30 ownership and escalation (INV30-GAP-006 · INV-30-C009)

| Role | Holder | Status |
|---|---|---|
| Accountable owner (artifact + API) | David Paul Russell — davidpaulrussell@linearfinance.org | **Proposed — confirm by signing `evidence/SIGNOFFS.json` → `owner`** |
| Architecture approver (ADR-0001) | David Paul Russell | Proposed — sign `architecture_approver` |
| Security reviewer | _unassigned_ | **Open** — must not be the author of the change under review |
| Independent verifier (release evidence) | _unassigned_ | **Open** — reproduces `release.py --verify` offline |
| On-call primary / secondary | _unassigned_ | Open — required before any production stage beyond canary |

## Escalation path

1. On-call primary (page, 15 min ack for SEV1/SEV2 — see `INCIDENT_RESPONSE.md`).
2. On-call secondary (auto-escalates after 15 min without ack).
3. Accountable owner (SEV1 always; SEV2 after 1 h unresolved).
4. Estate security contact for any suspected invariant breach (zero-budget SLO) — immediately, in parallel.

## Review path for changes

* Any change to `core.py`, `authz.py`, `service.py`, `backend.py`, `schemas/` or `policy.py` needs the
  owner **and** the security reviewer.
* Docs/runbook-only changes need the owner.
* Every review is recorded in the PR and referenced in `CHANGELOG.md`.

Named individuals other than the owner cannot be invented by the remediation pass; the open rows are tracked as
blockers in `WAIVERS.json` (none waived) and surface as conditions in the release gate.
