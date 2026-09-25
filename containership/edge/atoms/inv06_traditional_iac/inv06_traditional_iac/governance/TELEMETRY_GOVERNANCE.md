# Telemetry Governance (MC-049)

Status: **Draft.**
| Signal | Retention | Sampling | Privacy | Access |
|---|---|---|---|---|
| Metrics | 13 months | none | label allowlist `tenant, operation, outcome, dependency, code`; secret-like values refused | SRE, owner |
| Logs | 30 days hot, 1 year cold | INFO+ | `redact()` on all fields | SRE, security |
| Traces | 7 days | 10 % head, 100 % on error | no payloads, IDs only | SRE |
| Audit | ≥ 7 years (estate WORM) | none | redacted details | security, auditors |
Deletion: tenant offboarding deletes that tenant's state namespace; audit retained per legal hold. Incident preservation: freeze export of logs/audit for the incident window (`SignedAuditLog.export`).
