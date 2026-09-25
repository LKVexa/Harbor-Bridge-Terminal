# Telemetry governance (MC-045) and safe diagnostics (MC-043)

| Signal | Retention | Sampling | Access | Export | Privacy |
|---|---|---|---|---|---|
| Metrics | 30 d raw, 13 mo downsampled | none | SRE, owner | Prometheus remote-write (internal only) | tenant label capped at 1000 series/metric, overflow bucket |
| Logs | 14 d hot, 90 d cold | debug off in prod | SRE, owner; security for audit | internal SIEM | redaction mandatory (`security/secrets.redact`) |
| Traces | 7 d | 10 % head-sampled; 100 % for errors | SRE | internal only | attrs truncated 128 chars |
| Audit log | ≥ 1 y, immutable | none | security only | SIEM, WORM storage | redacted fields; HMAC-chained |
| Decision records | 90 d | none | SRE, owner | internal | inputs redacted |

Diagnostics endpoints must return bounded, redacted `status()`/`HealthReport` only; no raw
guest memory, no key material, no full tokens. Leakage tests: `SecretsTest`, `TelemetryTest`.
