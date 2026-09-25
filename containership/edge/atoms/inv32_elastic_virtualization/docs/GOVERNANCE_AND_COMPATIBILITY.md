# INV-32 Governance, Versioning and Compatibility (v4.3.0)

Machine-readable sources: `governance.json`, `waivers.json`, `tech_debt.json`, `compat_matrix.json`.

## Ownership — BLOCKED
`governance.json.owners` is intentionally `null`. An accountable service owner, security owner, on-call owner
and deputy must be named by the organisation. The production exit gate (`release.py gate`) fails while any is
null. Escalation chains, team boundaries (INV-33, PLN-05, GAP-10, INV-24) and review cadences are defined.

## Incidents
Severity triggers, paging targets, acknowledgement/escalation limits, containment actions, evidence
preservation and post-incident review rules are in `governance.json`; procedures in RUNBOOKS.md. Customer/tenant
communication ownership: service owner (BLOCKED until named).

## Waivers
Record fields: `id, requirement, rationale, risk, compensating_controls, owner, approver, issue, created_at,
expires_at, renewals, max_renewals`. `release.py gate` blocks expired waivers and surfaces high-risk ones.
Safety-relevant technical debt is tracked separately from ordinary backlog (`tech_debt.json`).

## Versioning policy
* Package: SemVer. MAJOR = breaking API/schema/state format; MINOR = additive; PATCH = fixes.
* Schemas: versioned independently (`family/major`, minor in `$id`). Package MINOR may add schema minors only.
* Support window: current minor and previous minor (N, N-1) receive security fixes.
* Minimum Python: 3.10 (bootstrap enforces).
* `PK_RESOURCE_ADJUSTMENT/1`: deprecated; removal 5.0.0 / 2027-06-30 (owner approval pending).

## Patching / EOL
| Severity | Patch SLA |
|---|---|
| Critical (reserve/tenant-isolation bypass, RCE) | 72 h, out-of-band release |
| High | 14 d |
| Medium | next minor, ≤ 90 d |
| Low | best effort |
Emergency release: branch from last release tag, single fix, full CI + evidence manifest, protected approval.
Dependency update cadence: monthly review (stdlib-only runtime today). End-of-support notice 6 months; EOL
notice 12 months. Unsupported versions: bootstrap `--check` flags them via the matrix; production use past EOL
requires an unexpired waiver.

## Mixed versions
See `compat_matrix.json.mixed_version`.
