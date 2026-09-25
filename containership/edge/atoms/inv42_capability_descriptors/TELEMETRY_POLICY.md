# Telemetry policy — INV-42 (MC-025)

| Signal | Content | Sampling | Retention | Export |
|---|---|---|---|---|
| Metrics | op, outcome, class, `table_fp`. Descriptor numbers are never used as labels. | 100% | 13 months (downsampled after 30 days) | Prometheus / OTel |
| Structured logs | Redacted event JSON | 100% of non-ok events; ok events configurable via `sample_ok` (default 1.0, production 0.01) | 30 days | Log pipeline with TLS |
| Traces | W3C traceparent ids on events | Head-based, follows the caller's flags | 7 days | OTel |
| Audit chain | Allow-listed event fields | 100%, never sampled | 1 year online plus 6 years archived, or longer if a legal hold applies | Append-only, WORM storage recommended |

## Privacy

The following never leave the process:

- auth tags
- table ids
- keys
- resource objects
- full wire payloads

This is enforced by `audit.FORBIDDEN_FIELDS`, `telemetry.redact`, and the tests.

The `owner` string is not emitted. Tenant and workload identity come from the caller's resource attributes on the log or trace pipeline, not from INV-42.

Access to the audit chain is limited to security and the owner, and is reviewed every 90 days (REVIEWS.json `access`).
