# GAP-10 Ownership

The checklist requires a single accountable engineering owner and an operational/on-call owner for every component. The package cannot assign people; these slots stay open until the owner fills them (exception EX-001).

| Scope | Engineering owner | On-call owner | Reviewer / approver |
|---|---|---|---|
| P0 components 01–08 | *unassigned* | *unassigned* | *unassigned* |
| P1 components 09–18 | *unassigned* | *unassigned* | *unassigned* |
| P2 components 19–28 | *unassigned* | *unassigned* | *unassigned* |
| P3 components 29–40 | *unassigned* | *unassigned* | *unassigned* |

Required identities (capabilities from `production/keys.py`):

| Identity | Capabilities |
|---|---|
| GAP-09 reporter(s) | `telemetry.publish` scoped to their node glob |
| Policy author | `policy.author` scoped to `site/*` |
| Policy relax approver (different person) | `policy.approve-relax` |
| On-call operator | `control.operate`, `control.release` |
| GAP-10 controller | `controller.lead` |
| Release engineer | `release.sign` |
