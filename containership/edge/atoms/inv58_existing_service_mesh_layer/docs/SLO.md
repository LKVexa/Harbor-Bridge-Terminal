# SLOs, error budgets and support (v4.3.0)

| SLO | Indicator (how measured) | Objective | Error budget | Burn handling |
|---|---|---|---|---|
| bounded attempts | `inv58_effective_attempts` ≤ route budget; every reconcile | 100 % | none | any violation = SEV1, freeze mutations |
| no bypass | every plaintext flow to a meshed destination produces `bypass.detected` within one scrape | 100 % | none | any miss = SEV2 |
| handoff cost | p99 of `mesh.map_identity` (bench) and `inv58_latency_seconds{operation="identity"}` | < 100 µs library p99; < 2 ms boundary p99 | 1 % of 28-day window may exceed | 2× burn over 1 h → page; 1× over 6 h → ticket |
| availability | readiness true / probe | 99.9 % monthly per site | 43 min | budget exhausted → change freeze except fixes |

Error-budget policy: when a budget is exhausted, releases are limited to reliability/security fixes until the 28-day window recovers; the component owner decides exceptions.

**Support commitments:** DRAFT — hours, on-call rota and response times are in `governance/OWNERSHIP.json` escalation levels, but no people are assigned, so nothing here is a commitment yet (INV-58-C091 PARTIAL).

## Recovery objectives
- RO-1: after a trust dependency recovers, the next request succeeds (0 extra failures).
- RO-2: no mutation lost or duplicated across restart (sealed snapshot + fencing).
- RO-3: audit chain verifies after every fault scenario.
- RO-4: admission in-flight accounting returns to zero after every burst.
All four are asserted by `tests/test_fault_injection.py`.
