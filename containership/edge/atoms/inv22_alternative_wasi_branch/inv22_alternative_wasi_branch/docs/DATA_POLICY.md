# Data inventory, retention and residency (MC-61)

| Data | Where | Contains personal data? | Retention (config key) | Notes |
|---|---|---|---|---|
| Certificates (signed bytes + index) | store `certs` | No | life of release + `retention.audit_days` | Revoked/superseded rows are kept as tombstones, never deleted by the component. |
| Audit events | store `audit` | Operator subject IDs | `retention.audit_days` (default 7 years) | Append-only; deletion requires an offline, owner-approved archive procedure. |
| Drift history | store `drift` | No | `retention.drift_days` | Immutable. |
| Config revisions | store `config_revisions` | Operator subject IDs | `retention.audit_days` | Secrets appear only as `secret://` references. |
| Telemetry | JSONL exporter | No (labels restricted to an allow-list) | `retention.telemetry_days` | Redacted before write. |

Residency: `retention.residency` must be set per deployment (default `unset`). **Open:** an automated retention/deletion job is not implemented; see `data/remediation.json` MC-61.
