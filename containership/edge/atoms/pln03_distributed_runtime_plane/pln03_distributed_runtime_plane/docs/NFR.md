# PLN-03 non-functional requirements (MC-004)

| ID | Objective | Measure | Budget | Evidence |
|---|---|---|---|---|
| NFR-LAT-01 | p99 `state_get` against a local adapter < 10 ms | `state_latency_seconds` histogram; `tools/bench.py` | 1 % may exceed | `evidence/bench.json` |
| NFR-LAT-02 | Governed-path overhead recorded per release | bench `overhead_governed_vs_core_p50_x` | regression > 25 % blocks release | bench |
| NFR-AVL-01 | Readiness ≥ 99.9 % monthly per site (cloud/datacenter), ≥ 99.5 % (near/far-edge) | `/health.ready` | error budget per month | fleet telemetry (not in archive) |
| NFR-DUR-01 | Zero loss of accepted publishes | fault suite invariant | none | test_mc043 |
| NFR-DUR-02 | RPO 0 for journaled adapters (fsync per record); RTO ≤ 5 min restore from journal copy | DR test | — | test_mc047_mc050 |
| NFR-CON-01 | Consistency per site from config: strong / read-your-writes / eventual; failover never weakens below configured level | `select_failover` | none | test_mc039 |
| NFR-ISO-01 | Zero cross-tenant reads | isolation + fuzz suites | none | test_mc031, fuzz |
| NFR-SEC-01 | Zero calls served without binding and valid token | `capability_denials` counter + audit | none | test_mc013 |
| NFR-DET-01 | Identical inputs + config digest ⇒ identical outcome codes (no time-dependent branching outside tokens/deadlines, both clock-injected) | fixture determinism | none | test_mc018 |
| NFR-RES-01 | Bounded memory: every queue/buffer/series/audit ring has a ceiling in `Limits`/`MAX_SERIES` | code review + tests | none | test_mc045_metric_cardinality, test_mc009 |
| NFR-RES-02 | Retries add ≤ 20 % load (`retry_budget_ratio`) | `retries` counter / calls | 20 % | test_mc037_retry_budget |
| NFR-PWR-01 | Power per 1k ops on far-edge class | **not measured** — requires target hardware | open | MC-044 open item |
