# SLOs, error budgets and support policy (checklist #90, #62, DRAFT — thresholds PROPOSED)

| SLO | Objective | Budget | Burn alerts |
|---|---|---|---|
| no leakage | zero values in logs/errors/metrics/traces | none — any breach is SEV1 | immediate |
| scoping | zero resolutions outside scope | none — SEV1 | immediate |
| resolve latency (cached) | p99 < 5 ms, p50 < 1 ms, max < 50 ms | 1 % of requests over p99 target / 30 d | 14.4× (1 h), 6× (6 h) |
| availability | 99.95 % successful-or-correctly-denied | 21.6 min / 30 d | 14.4× (1 h), 6× (6 h) |
Budget exhausted → feature freeze; only reliability/security changes ship. Support: current minor + previous minor receive security fixes (see SECURITY.md).
