# Observability

| ID | INV55-OPS-OBS | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| # | Capability | Implementation | Gaps |
|---|---|---|---|
| 52 | Stall detector | `health()["stalled"]` when in-flight > 0 and no progress for `stall_after_s` | `tests/test_service_contract.py::LifecycleContract.test_stall_detector` |
| 71 | Health/status | `SecretsService.health()`: live, ready, state, reason, stalled, version, release, protocols, config provenance, policy digest, provider/circuit/audit head, leases, in-flight | Not served over HTTP; unauthenticated |
| 72 | Metrics | `telemetry.py::Metrics` counters + histogram, Prometheus text | No exporter, no saturation gauges |
| 73 | Logs | `JsonLogger`: JSON lines with ts, level, component, event; redacted | Only state transitions and `internal_error` (class name only) logged; no schema version field |
| 74 | Tracing | `Tracer`: W3C `traceparent` in `request["traceparent"]` (malformed values tolerated → new trace), one span per op, error code attr; `tests/test_config_audit_telemetry.py::TelemetryTests.test_trace_propagation` | No child spans for provider/audit; no export |
| 75 | High-cardinality diagnostics | Decision ledger (bounded ring) instead of labels | — |
| 76 | Decision ledger | `DecisionLedger.add` from `_decision` for resolve/use/rotate/scope allow and all guard denials | revoke, retire, freeze, config changes not recorded in ledger (they are audited) |
| 77 | Operator explain view | `DecisionLedger.explain(request_id)` (`TelemetryTests.test_service_propagates_trace_and_explains`) → decision, why, who, what, policy/config/release digests, trace_id | No UI/API; operator-only access MUST be enforced by host |
| 78 | Release lineage | `release`, config digest, policy digest in ledger and `health()` | No infra-graph correlation |

Example explain output shape (values illustrative, `<redacted>` where sensitive):
```json
{"request_id":"<id>","decision":"denied","why":"out_of_scope",
 "who":{"tenant":"<tenant>","subject":"<app>"},"what":{"operation":"resolve","secret":"<redacted>"},
 "evaluated_against":{"policy":"sha256:<digest>","config":"sha256:<digest>","release":"4.3.0"},"trace_id":"<trace>"}
```

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Stall detector test |
| 4.3.0 | 2026-09-22 | Internal-error logging, tracer tolerance, tests |
