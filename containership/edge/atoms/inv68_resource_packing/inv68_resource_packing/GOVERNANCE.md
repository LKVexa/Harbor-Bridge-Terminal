# INV-68 governance (MC-03, MC-04, MC-39)

Everything here needs named people. Code only makes the gaps visible
(`tools/governance_check.py` → `evidence/GOVERNANCE.json`, a release-gate input).

| Artifact | Purpose | State |
|---|---|---|
| `ops/owners.json`, `CODEOWNERS` | accountable/service/security owners, reviewer, release manager, policy admin; support boundary; escalation chain | roles defined, **no assignees** |
| `ops/ADR-0001-resource-packing.md` | architecture decision | **PROPOSED**, no approvers |
| `ops/REVIEWS.json` | access, policy, dependency, architecture, threat-model, drill and register reviews with cadence | **never performed** |
| `ops/REGISTER.json` | exceptions / technical debt / deprecations with owner, approvers, risk, compensating controls, expiry | 4 entries **proposed**, unowned |
| `LICENSING.md` | distribution license | **UNDECIDED** |
| `SECURITY_RESPONSE.md` | vulnerability intake, SLA, EOL | intake **UNASSIGNED** |

Expiry enforcement: the gate fails on expired or unowned waivers; governance_check
fails on overdue reviews and unowned register entries. Reporting: `GOVERNANCE.json`
lists every open item; `REQUIREMENTS_TRACEABILITY.md` shows which controls they block.

To close the governance tier: fill assignees in `ops/owners.json` (+ CODEOWNERS
handles), sign ADR-0001, choose a license, assign the security intake, perform the
first review round (set `last` dates), and approve or reject each register entry.
