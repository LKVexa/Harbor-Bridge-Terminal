# SLO envelope (item 38)

| SLI | Target | Measurement point | Local evidence |
|---|---|---|---|
| Silent drops | 0 | fuzz P1/P2, adversarial | pass |
| Translation latency p99 | < 5 ms | `translate()` wall time, reference benchmark | ~0.12 ms (evidence/perf/latest.json) |
| Reconcile throughput (controller CPU only) | ≥ 200 workloads/s over fakes | benchmark harness | ~1.6 k/s |
| Time-to-Placed (create → status Placed) | p99 < 5 s at 100 creates/s | real cluster | **not measured (EXC-007)** |
| Status freshness | runtime change reflected < 30 s | real cluster | **not measured** |
| Controller availability | 99.9 % leader present | Lease metrics | **not measured** |
| Error budget | 0.1 % of reconciles may exceed latency targets | Prometheus | — |
