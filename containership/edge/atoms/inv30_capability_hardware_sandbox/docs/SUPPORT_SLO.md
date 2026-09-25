# SLOs, error budgets, support (INV30-GAP-061 · INV-30-C091)

| SLO | Objective | Budget | Burn response |
|---|---|---|---|
| bounds | zero OOB successes | **none** | any occurrence = SEV1, emergency disable |
| monotonicity | zero widening derivations | **none** | SEV1 |
| invalidation | zero post-invalidation uses | **none** | SEV1 |
| truthful enforcement | zero `cheri-hardware` records without hardware | **none** | SEV1 |
| availability (service wrapper) | 99.9 % monthly successful non-refused requests | 43 min/month | 2 %/h burn → page; 5 %/6 h → ticket; budget exhausted → change freeze |
| latency | p99 access ≤ 5 ms | 1 % of minutes | ticket |

Support commitment (proposed, owner to confirm): business-hours support for model-only deployments; 24×7 paging
only once on-call rows in OWNERSHIP.md are staffed. Invariant violations page 24×7 regardless.
