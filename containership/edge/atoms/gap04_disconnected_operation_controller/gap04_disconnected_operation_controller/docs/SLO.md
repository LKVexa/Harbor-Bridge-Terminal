# GAP-04 SLO and Error-Budget Specification (proposed)

**Status:** proposed targets — require owner approval (W-001). Targets derive from safety requirements, not from the best observed benchmark. **Controls:** C38-006/015, C50.

| SLI | Definition (Prometheus) | Mode | Objective | Window | Budget |
|---|---|---|---|---|---|
| Lease enforcement | decisions accepted with expired/absent lease | all | **0** | always | none — any event is SEV1 |
| Tier correctness | decisions above permitted tier | all | **0** | always | none |
| Record completeness | acknowledged decisions missing from reconciliation record | all | **0** | always | none |
| Safety-readiness availability | `ready=true` share, excluding `no_lease` during authorized maintenance | connected | 99.9% | 30 d | 43 min |
| Decide latency | `histogram_quantile(0.99, rate(gap04_decision_latency_seconds_bucket[5m]))` | disconnected | p99 ≤ 50 ms | 30 d | 1% of 5-min windows |
| Durable decision success | 1 − (E04xx denials / attempts) | disconnected | 99.99% | 30 d | 0.01% |
| Reconciliation convergence | reconnect→`reconcile.complete` | reconnect | 99% ≤ 5 min for ≤ 10k decisions | 30 d | 1% |
| Stale-policy exposure | time with `policy.stale=true` while partitioned | disconnected | ≤ 0 (decisions refused at bound) | — | — |

**Not counted against budget:** expected partitions (GAP-12 root cause) while tier/lease behave per schedule; `E0101/E0102/E0100` refusals that are correct policy outcomes. **Counted:** E04xx storage, E0300 time, E05xx fencing, E06xx reconcile failures, E07xx overload.

**Burn-rate alerting:** page at 14.4× (1 h) and 6× (6 h) budget burn; ticket at 1× (3 d). **Budget exhaustion:** feature rollouts halt; only fixes and security patches ship until the budget recovers. Exclusions must be decided before an incident, never retroactively.

Maximum tolerated time in degraded states: `stale policy` ≤ `max_policy_staleness_s`; `unreconciled after reconnect` ≤ 30 min; `safety-not-ready` while connected ≤ 15 min.

**Backtest:** `evidence/perf_baseline.json` measured p99 well under 50 ms on the build host; representative edge hardware is required before approval (W-010).
