# Governance (C094, C098, C099)

Patching/vulnerability SLA — **PROPOSED**: critical 7 days, high 30 days; end of life
one minor release after supersession. Not in force until an owner accepts it.

Recurring reviews — **PROPOSED**: quarterly access/policy/config review, per-release
dependency review (currently zero third-party runtime dependencies).

## Exceptions, waivers and debt register
| ID | Item | Owner | Expiry | Notes |
|---|---|---|---|---|
| W-01 | pk_core unpinned | UNASSIGNED | none set | gate cannot run |
| W-02 | Dandelion unresolved | UNASSIGNED | none set | C011 DAG, C031 |
| W-03 | Gateway serialises admission under one lock | UNASSIGNED | none set | measured in bench |
| D-01 | `Instance.leave()` without scope id (compat path) | UNASSIGNED | 5.0.0 | deprecated |
Machine-readable copy: `WAIVERS.json`.
