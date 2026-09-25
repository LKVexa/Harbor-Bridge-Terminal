# INV-25 ownership and escalation (work item 6 — C009, C097)

Ownership is role/team based so it survives personnel turnover. **Named assignments are
PENDING owner confirmation** (waiver W-0001); tooling cannot appoint people.

| Role | Identifier | Responsibility | Named holder |
|---|---|---|---|
| Accountable component owner | `@inv25-owners` | Final authority on catalogue scope, releases, waivers | PENDING |
| Primary maintainer | `@inv25-maintainers` | Code, tests, triage | PENDING |
| Secondary maintainer | `@inv25-maintainers` | Backup for the above | PENDING |
| Security reviewer | `@inv25-security` | Class lists, surface widening, authz, provenance, SECURITY.md | PENDING |
| Release approver | `@inv25-release` | Gate sign-off, signing-key custody | PENDING |

## Upstream / downstream owners (from `contract.py`)

| Dependency | Direction | Owner identifier |
|---|---|---|
| GAP-13 Policy engine | upstream | `@gap13-owners` (PENDING) |
| INV-24 MicroVM runtime | downstream | `@inv24-owners` (PENDING) |
| INV-35 High-performance VM I/O | downstream | `@inv35-owners` (PENDING) |
| INV-26 MicroVM snapshotting | peer | `@inv26-owners` (PENDING) |
| INV-43 Transient-execution defense | optional peer | `@inv43-owners` (PENDING) |

## Approval rules (enforced by `CODEOWNERS` + `store.py`)

- Device additions, version changes and **any surface widening** need the component owner;
  in code, a candidate cannot be activated without an approver distinct from its proposer, and
  widening needs the `catalogue.widen` capability.
- Changes to `FORBIDDEN_CLASSES` / `PERMITTED_CLASSES`, `authz.py`, `provenance.py` need the
  security reviewer (`CODEOWNERS`).
- Owner references are re-validated at every recurring review (`docs/recurring-review.md`).

## Escalation

See `docs/incident-response.md` for severity levels, response targets and the escalation
chain, including the paths for a **deployment blocked by the catalogue** and an
**unauthorized surface-growth event**.
