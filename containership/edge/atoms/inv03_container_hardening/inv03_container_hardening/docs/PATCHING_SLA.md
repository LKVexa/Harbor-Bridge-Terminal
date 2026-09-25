# Patching, vulnerability and EOL SLA — INV-03 (checklist item 57)

**Status: PROPOSED** — numbers need owner approval.

| Severity (CVSS v3.1 / exploitation) | Fix in baseline or runtime floor | Emergency path |
|---|---|---|
| Critical, or known exploited (KEV) | 48 hours | raise `runsc` minimum version in a signed baseline; nodes below it stop receiving pods |
| High | 7 days | same |
| Medium | 30 days | next scheduled baseline |
| Low | 90 days | next scheduled baseline |

- Supported window: current gVisor release and the previous one; older releases are refused by `RuntimeInventory` via the minimum-version floor.
- Python: the package supports CPython versions still receiving security fixes (currently 3.10–3.13).
- EOL rule: a runtime or interpreter that leaves upstream support is removed from the approved matrix within 30 days.
