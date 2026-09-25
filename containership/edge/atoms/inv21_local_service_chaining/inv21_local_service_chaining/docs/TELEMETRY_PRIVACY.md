# Telemetry Privacy, Retention, Sampling and Export

* **Never recorded**: request/response payloads, credentials, identity keys, handler exception text (kept only in protected `ChainError.diagnostics`, not exported).
* **Pseudonymised**: principal subject → keyed HMAC pseudonym (`p-<16 hex>`); key per process unless `redact_key` is configured (configure it fleet-wide to correlate across hosts).
* **Kept in clear**: tenant id, callee name, trace id, route, reason, error code, depth, config/policy revision — needed for isolation SLOs and explainability.
* **Cardinality**: ≤256 values per label, ≤2048 series; overflow → `__other__` and `dropped_series`.
* **Retention**: decision ring `max_telemetry_events` (default 1024) and `max_age_s` (default 1 h) in memory; audit JSONL retention is an estate policy (recommend ≥ 400 days, immutable storage).
* **Sampling**: refusals are always kept; successful routes sampled at `telemetry_sample_rate`.
* **Export**: Prometheus text at `/metrics`; audit via JSONL file sink; explain view via `Chainer.explain(trace_id)` (operator-only).
