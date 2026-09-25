# SLO measurement (M39)

| SLO | SLI source | Budget | Enforcement |
|---|---|---|---|
| isolation | `pk_isolation_violation_total` (service cross-scope guard) + security tests | none | any violation BLOCKs release (`tools/release_gate.py`) |
| restart_continuity | fault suite restart scenarios (`evidence/fault-results.json`) | none | BLOCK |
| revocation_durability | fault suite + restore guard | none | BLOCK |
| call_overhead | `benchmarks/harness.py` (`evidence/performance-results.json`) | 1% of dispatches may exceed 1 ms | burn > 1.0 BLOCKs |

Measurements are local-host numbers from the release run. Fleet-level SLO measurement needs a production telemetry backend (not in this archive) — recorded as a condition, not a pass.
