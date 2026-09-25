# INV-17 Metrics

**Controls:** C072 (metrics exporter), C078 (release lineage), C075 (label guard)
**Owner:** UNASSIGNED — owner to fill

Exporter: `observability::MetricsExporter(registry, lineage).render()` — Prometheus text
exposition 0.0.4. Served at `/metrics` by `observability::serve_status` (optional, loopback).
Values are aggregated over `control::StreamRegistry.streams()` at scrape time from `Stream.stats()`.

## Metric catalogue (exactly `MetricsExporter.HELP`)

| Name | Type | Labels | HELP text | Source |
|---|---|---|---|---|
| `inv17_streams_open` | gauge | `state` | Open streams by lifecycle state | count of `StreamStats.state` |
| `inv17_credit_stalls_total` | counter | — | Writes refused for lack of credit | Σ `credit_stalls` |
| `inv17_elements_transferred_total` | counter | — | Elements accepted by writers | Σ `transferred` |
| `inv17_elements_read_total` | counter | — | Elements delivered to readers | Σ `reads` |
| `inv17_elements_dropped_total` | counter | — | Buffered elements reclaimed on reader drop | Σ `dropped_items` |
| `inv17_elements_buffered` | gauge | — | Elements currently in flight | Σ `buffered` |
| `inv17_duplicate_writes_total` | counter | — | Idempotent retries acknowledged without enqueue | Σ `duplicate_writes` |
| `inv17_dropped_end_streams` | gauge | `end` (`reader`/`writer`) | Streams with a dropped end, by end | count of `reader_dropped`/`writer_dropped` |
| `inv17_load_shed_total` | counter | — | Writes shed by quota or overload | `StreamRegistry.shed_count` |
| `inv17_breaker_open` | gauge | — | 1 when the admission circuit is open | `breaker.state == "open"` |
| `inv17_disabled` | gauge | — | 1 when emergency disable is active | `StreamRegistry.disabled` |
| `inv17_audit_events_total` | counter | `kind` | Security audit events by kind | count of `registry.audit.events` by `AuditEvent.kind` |
| `inv17_health_status` | gauge | `status` (`healthy`/`degraded`/`unhealthy`/`disabled`) | 1 for the current health state | `StreamRegistry.health().status` |
| `inv17_build_info` | gauge | `component`, `version`, `build`, `revision`, `instance` | Release lineage | `Lineage.labels()` |

`state` values: `open`, `credit_stalled`, `frozen`, `ended`, `reader_dropped`, `writer_dropped` (`stream::Stream.state`).

## Semantics caveats

- "Counters" are sums over **currently registered** streams. `StreamRegistry.close` removes a
  stream, so its contribution disappears and the `_total` series can **decrease**. Use
  `rate()`/`increase()` with care; Prometheus treats a decrease as a counter reset.
- `inv17_load_shed_total` counts both tenant-quota sheds and global-budget sheds; the registry
  does not export them separately (use `explain()` decision reasons).
- `inv17_streams_open` includes ended/dropped streams until `close` is called.
- Auth denials, replays, trust outages and quota-denied opens are counted via `inv17_audit_events_total{kind}` (sum over the in-memory ledger; each scrape also evaluates `health()`). No metric exists for type mismatches or latency; details are in the audit ledger (`AuditLedger.export_jsonl`), the decision log
  (`observability::explain`) and structured logs. The contract signal "dropped_end_errors counter by
  which end dropped" is approximated by the `inv17_dropped_end_streams` gauge.

## Guards

- `ALLOWED_LABELS` = {state, end, reason, tenant_hash, workload_hash, code, status, kind}; any other label (except on `inv17_build_info`) raises `ValueError`.
- `MAX_SERIES` = 10 000 samples per scrape, else `RuntimeError`.
- Label values escaped by `_esc`.
- No per-tenant labels are emitted today.

Tests (planned): `tests/test_observability.py`.
