# Telemetry retention/sampling/privacy/export (INV-38-C079)

Telemetry is classified (metrics/logs/traces/security_audit/diagnostics/
release_evidence) with distinct retention and access (`observability/retention.yaml`,
`telemetry_policy.py`). Mandatory security audit events are never sampled out.
Data minimization/redaction/tenant isolation apply before export; destinations are
allowlisted and encrypted. Conformance tests in `tests/test_telemetry_policy.py`
prove ordinary tenant config cannot weaken sampling/retention/redaction. **Status:**
`DONE`.
