# GAP-15 Operations Contract

## SLOs (carried from the v4.2.0 contract, unchanged)

| SLO | Objective | Error budget | Measured by |
|---|---|---|---|
| no inference | zero `certified` verdicts without a recorded exact-key result | none | `state.certify` returns `untested` for any key without evidence; tests `test_no_cross_partition_evidence_reuse` |
| expiry | zero expired positive certifications treated as current | none | `effective_expiry`; offline `R_OFFLINE_ENTRY_EXPIRED` |
| eol enforcement | zero rollouts certified onto an EOL runtime | none | lifecycle precedence; `GAP15EOLAdmitted` page |
| availability (proposed) | 99.9% successful `certify` over 30d | 43m/30d | `gap15_requests_total{op="certify"}` |
| latency (proposed) | p99 `certify` < 50 ms at the measured envelope | — | `gap15_request_seconds` |

Proposed objectives are **not accepted** until an owner signs them (MC-43, MC-xx-17).

## Metrics

All metrics are declared in `production/observability.py::METRIC_DEFS` with type, unit, help text and a
closed label vocabulary. Counters are process-lifetime and reset on restart (use `rate()`/`increase()`);
gauges are recomputed by `update_gauges()`; the histogram uses fixed buckets
`0.001 … 5 s`. Scrape interval: 15 s. `gap15_exporter_scrape_age_seconds` measures the exporter itself.
Raw artifact, node, trace and signer identifiers are **never** label values.
