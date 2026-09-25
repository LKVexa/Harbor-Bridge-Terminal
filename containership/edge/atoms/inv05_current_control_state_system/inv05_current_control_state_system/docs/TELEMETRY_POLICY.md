# Telemetry privacy, retention and export policy

Traceability: C075, C079; MC-036, MC-032-01, MC-033, MC-034.

| Signal | Classification | Contents | Retention | Sampling / cardinality |
|---|---|---|---|---|
| Metrics | internal | catalog in `observability.METRIC_CATALOG`; labels are op/result/action/state only — never tenant, key or subject | 30 d raw, 13 mo downsampled | ≤ 64 series per metric (overflow bucket) |
| Structured logs | internal / confidential | `cstate.log/1`; subject hashes, request ids, revisions; values never logged | 30 d hot, 90 d archive | per-event token bucket; suppressed counts reported |
| Traces | internal | allow-listed attributes only | 7 d | head 5 % parent-based; errors always kept |
| Explain records | confidential | predicates, branch, policy version, config hash; pseudonymous subject | in-process ring (5000) + export on request | authorized `admin.explain` only |
| Audit log | confidential, integrity-critical | security events | ≥ 1 y (WORM archive) | none |
| Values/keys of tenants | tenant-sensitive | **never exported in telemetry** | — | — |
| Secrets | secret-prohibited | never emitted | — | — |

Approved exporters: Prometheus scrape over mTLS, JSON logs to the platform collector in the same residency region, OTLP traces to the regional collector. Cross-region export of confidential signals is prohibited. Regulated-data deletion: logs/traces carry no tenant values; subject hashes are rotated by re-salting on tenant offboarding (procedure in RUNBOOK_DAY2).
