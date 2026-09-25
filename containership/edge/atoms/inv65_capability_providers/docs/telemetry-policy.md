# Telemetry policy (C079)

Metrics: no tenant/component labels (cardinality + privacy); retained 30 d. Logs: JSON, secrets redacted at source, retained 14 d; security audit events retained ≥ 1 y and are append-only. Traces: W3C traceparent; sample 1% of successes, 100% of errors; attributes redacted. Export: via the operator's collector only; nothing phones home.
