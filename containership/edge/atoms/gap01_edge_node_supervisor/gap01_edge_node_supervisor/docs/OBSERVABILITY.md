# GAP-01 Observability

## Metrics (Prometheus text at `/metrics`, prefix `gap01_`)

| Metric | Type | Labels (bounded) | Meaning |
|---|---|---|---|
| `requests_total` | counter | `op`, `outcome` (ok/error/replayed), `code` (error catalog) | rate, errors, replays |
| `request_seconds` | histogram | `op` | latency |
| `state` | gauge | `state` | current lifecycle state (1) |
| `resident_workloads` | gauge | — | backlog/occupancy |
| `under_pressure` | gauge | — | saturation |
| `drain_deadline_breaches_total` | counter | — | drain SLO risk |
| `cordon_ack_overdue_total` | counter | — | cordon latency SLO risk |
| `emergency_entries_total` / `watchdog_hangs_total` | counter | — | safety events |

Label values outside declared domains collapse to `other` (cardinality bound).

## Logs

JSON lines on stderr (journald). Stable `event_id`s: `GAP01-START`, `GAP01-BOOT`, `GAP01-TRANSITION`, `GAP01-PARTITION`, `GAP01-EMERGENCY`, `GAP01-REQ-ERR`. Correlation fields: `request_id`, `trace_id`, `op`, `code`, node. Keys matching `secret|token|key|password|sig|mac|credential` are redacted; strings truncated at 1 KiB.

## Traces

`Tracer` accepts W3C `traceparent`, nests spans, and exports via a pluggable callable (OTLP exporter not shipped — EXC-013). Every audit record carries the `trace_id`.

## Decision reasons / explain view

Every transition records `last_reason`; every mutating request is an audit record (caller, args redacted, resulting state, generation, trace_id); `diagnostics` returns the explain bundle (status, config + provenance, recovery report, breaches, SLO report, audit head, recent spans, pressure, inventory, runtime-observed set).

## Retention and privacy

Audit: `audit_retention` records (rotate externally; chain verification tolerates rotation by anchoring at the first retained record). Spans: last 1024 in memory. Logs: journald policy. Diagnostics never include key material. Sampling: none (volumes are low); OTLP sampling is exporter-side.

## Units, semantics, compatibility

Durations are in seconds (`_seconds`). Counters reset on process restart, so consumers should use `rate()` or `increase()`. Gauges are sampled on every request and every tick. Metric names, label names and log `event_id`s are part of the `/1` contract, and `tests/test_production.py::TelemetryContractTest` pins them. A rename requires a changelog entry and a deprecation period of one minor release. `gap01_build_info{version}` ties every series to the deployed build, and the `GAP01-START` log carries `version`.

## SLI/SLO formulas

| SLO | SLI | Window | Objective |
|---|---|---|---|
| transition legality | illegal transitions applied ÷ transitions attempted | 30 d | 0 (no budget) |
| drain completeness | nodes reporting `stopped` with residents | 30 d | 0 (no budget) |
| cordon latency | cordons acked later than `cordon_ack_timeout_s` ÷ cordons | 30 d, min 20 cordons | ≤ 1 % |

`controller.slo.report()` computes these locally. Alerting on the no-budget SLOs pages on any occurrence.

## Telemetry failure policy

A span exporter that fails is suppressed. The span ring is bounded, so an exporter can never block the control loop (`TelemetryContractTest::test_exporter_loss_does_not_affect_control`). Logs go to stderr (journald). A stalled log sink is not guarded in-process (open item).
