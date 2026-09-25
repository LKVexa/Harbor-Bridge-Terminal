# INV-35 SLOs, error budgets and support commitments (C091)

Approval: **PENDING** (accountable_owner, operations_owner).

| SLO | SLI | Objective | Window | Error budget | Burn-rate alerts |
|---|---|---|---|---|---|
| Memory safety | descriptors accepted outside registered memory | **0** | always | none — any event is SEV1 | immediate page |
| Liveness | completions with pending>0 that did not notify | **0** | always | none | immediate page |
| Isolation | cross-tenant accepts | **0** | always | none | immediate page |
| Readiness | fraction of minutes `inv35_ready==1` | 99.95 % | 30 d | 21.9 min | 14.4× over 1 h (page), 6× over 6 h (ticket) |
| Submit latency (reference) | p99 `inv35_submit_latency_us` | ≤ 1 000 µs | 30 d | 1 % of 5-min windows | ticket |
| Throughput (production) | p50 vs backend line rate | ≥ 90 % | 30 d | 5 % below | backend-owned |

**Budget policy.** When a budget is exhausted: freeze feature rollouts for INV-35,
only reliability/security changes ship until the budget recovers.

**Support commitments.** Release-blocking defect acknowledgement ≤ 4 business h;
SEV1 ≤ 15 min; security reports per `SECURITY.md`. Supported versions: latest
MINOR of the current MAJOR plus the previous MINOR for 90 days.
