# INV-13 Interface Telemetry Data Residency & Privacy Policy (MC-029)

Enforced in code by `host/telemetry.py::PrivacyFilter` (allowlist) and applied before audit writes (`host/audit_sink.py`) and structured logs.

| Field class | Fields | Treatment | Export | Retention (default) |
|---|---|---|---|---|
| public | capability, op, outcome, code, world, rule_id, policy_digest, release, node, count, latency_us, reason, action, seq | clear (strings truncated to 256) | any region | metrics 13 months, logs 30 days |
| pseudonymise | tenant, workload, component | HMAC-SHA256 with a **per-region salt**, 64-bit prefix | in-region only | 90 days |
| hash | path, host_root, logical, requested, normalized, url, host | HMAC-SHA256 per-region salt | in-region only | 90 days |
| drop | secret, env, argv, token, body, headers, stack | never stored | — | — |
| unknown | anything else | **dropped** (allowlist) | — | — |

* Audit records: retained 1 year in-region, then deleted unless under legal hold; chains are verified before deletion windows close.
* Region salts are per region and rotated annually; rotating the salt makes older pseudonyms unlinkable (intended).
* Traces carry only W3C `traceparent` IDs, never payloads.
* Open items: legal sign-off on retention periods and the region list (`<<privacy officer>>`).

Evidence: `tests/test_ops.py::Audit.test_privacy_filter_applied_before_write`, `Telemetry.test_structured_log_privacy_and_bound`, `tests/test_integration.py::test_happy_path_and_audit` (host path absent from durable audit).
