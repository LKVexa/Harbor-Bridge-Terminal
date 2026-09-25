# Production SLOs and error budgets (G13-MC-046)

| SLI | Objective | Error budget | Measurement |
|---|---|---|---|
| Deny by default | 0 allows without a matching allow rule | none | property tests + `default_denies` vs `verdicts` |
| Determinism | identical request+bundle → identical verdict | none | property + golden tests every release |
| Explainability | 100 % of verdicts name rule (or null default-deny) and bundle identity | none | schema validation |
| Evaluation latency (service path, ≤10 000 rules) | p99 ≤ 2 ms, p50 ≤ 0.5 ms on reference hardware | 0.1 % of 5-min windows | `g13_evaluate_latency_ms` |
| Availability of `/v1/evaluate` (ready replicas) | 99.95 % monthly | 21.9 min/month | `/v1/ready` probes |
| Bundle freshness | active bundle age < warning threshold 99.9 % of time | 43 min/month | `g13_bundle_age_seconds` |
| Bundle activation | verify+activate ≤ 3 s for 10 000 rules | — | bench `load_ms` |
| Support response | SEV1 ack 15 min, SEV2 30 min | — | `RUNBOOKS.md` |

## Performance {#performance}
Release gate thresholds live in `ops/release_gate.json`; baseline in `ops/perf_baseline.json` (reference run, Linux x86-64, CPython 3.11). Regressions beyond +50 % of baseline or beyond the absolute ceilings block the release.

These commitments are **proposed** until approved by the service owner (OWNERS.yaml).
