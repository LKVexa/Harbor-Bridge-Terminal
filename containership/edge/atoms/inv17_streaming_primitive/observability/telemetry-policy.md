# INV-17 Telemetry Retention / Sampling / Export Policy

**Controls:** C079 (with C073 logging)
**Owner / approver:** UNASSIGNED — owner to fill
**Status:** All retention and export values below are **PROPOSED** and unapproved.

## Implemented mechanisms

| Mechanism | Behaviour | Code |
|---|---|---|
| Log level filter | `debug`<`info`<`warning`<`error`; default `info` | `StructuredLogger.LEVELS`, `level` |
| Head sampling | Only `debug` and `info` records are sampled at `sample_rate` (default 1.0); `warning`/`error` are always emitted; `sampled_out` counts drops | `StructuredLogger.log` |
| Trace sampling | Honours `sampled` flag from `traceparent` in the context object; no sampling decision is taken by INV-17 | `TraceContext` |
| Metrics | Pull on scrape; no internal retention | `MetricsExporter` |
| Audit | In-memory, unbounded, exported via `export_jsonl()` | `AuditLedger` |
| Decisions | Last 256 in memory | `StreamRegistry.decisions` |

Note: the code comment says "errors and security events are never sampled out", but sampling is
decided **only by level**. Security-relevant records must therefore be logged at `warning` or above
to be guaranteed. (Audit events are separate and never sampled.)

## PROPOSED retention

| Signal | Retention | Sampling |
|---|---|---|
| Metrics | 15 days raw, 13 months downsampled | none |
| Logs `warning`/`error` | 30 days | none |
| Logs `info` | 7 days | 10% in production (`sample_rate=0.1`) |
| Logs `debug` | off in production | — |
| Traces | 7 days | parent-based |
| Audit export | 1 year, write-once storage, with external `anchor()` recorded at each export | none |

## PROPOSED export

- Destinations: organisation's metrics and log pipelines; encrypted in transit (TLS) — INV-17 itself only writes to a text stream / serves loopback HTTP.
- Residency: telemetry stays in the deployment's region; pseudonymised identifiers only (set `INV17_TELEMETRY_SALT`).
- Access: see `observability/diagnostic-policy.md`.

Tests (planned): `tests/test_observability.py` (sampling never drops warning/error).
