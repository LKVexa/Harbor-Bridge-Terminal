# Telemetry privacy, retention and sampling

| ID | INV55-SEC-TELEMETRY | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Signal | Content | Retention | Sampling |
|---|---|---|---|
| Metrics (`Metrics`) | bounded label alphabet, no names/values, max 2 000 series | collector policy: 13 months (proposed) | none |
| Logs (`JsonLogger`) | all str fields `redact_text`-ed | 30 days (proposed) | none |
| Traces (`Tracer`) | W3C trace/span ids, attrs redacted; in-memory ring 10 000 | export NOT IMPLEMENTED | 100 % in memory |
| Decision ledger | tenant, subject, secret name, reason, digests; ring 10 000 | in memory only | none |
| Audit | see secret-name-privacy.md | 1 year minimum (proposed) | none |

- No values in any signal (SRS-042/051). Redaction is pattern-based (`errors.py::_SECRETISH`) and not exhaustive; unknown secret shapes would only be caught if passed as `known`.
- Exporters (OTLP, Prometheus HTTP endpoint): NOT IMPLEMENTED; `Metrics.exposition()` returns text for the host to serve.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
