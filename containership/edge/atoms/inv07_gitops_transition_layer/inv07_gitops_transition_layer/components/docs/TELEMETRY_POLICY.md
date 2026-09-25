# Telemetry retention and privacy policy (PROPOSED)

| Signal | Sensitivity | Sampling | Retention | Redaction | Access |
|---|---|---|---|---|---|
| Metrics | low (bounded labels: outcome, reason code, dependency) | none | 30 d (config `telemetry.retention_days`) | no free text in labels; cardinality cap 200 series/metric | `metrics.read` |
| Structured events | medium (tenant, site, ref, codes) | none at info+ | 30 d | `redact.scrub` centrally; 8 KiB cap | operators |
| Traces | medium | `telemetry.trace_sample_ratio` | 7 d | attributes scrubbed, ≤ 16 attrs | operators |
| Explain records | high (decision lineage) | none | = audit retention | scrubbed | `explain.read` |
| Audit ledger | high | none | ≥ 1 y, WORM; archive only after export+seal | scrubbed at write | security |

Residency: export destinations must pass `ResidencyPolicy.check("telemetry", region)`. Deletion: telemetry past retention is dropped by the backend; audit is never deleted in place. Privacy review: **pending** (no reviewer assigned).
