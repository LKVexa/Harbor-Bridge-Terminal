# Secret-name privacy

| ID | INV55-SEC-NAMEPRIVACY | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Classification: secret **names** are CONFIDENTIAL metadata (they may reveal systems/customers); values are SECRET.

| Sink | Contains name? | Code |
|---|---|---|
| Local audit file | Yes, plaintext | `_audit` (`"secret": name`) |
| Metrics | No (labels: op, outcome, reason, to) | `service.py` metric calls |
| Logs | Only state transitions logged by service; no names | `_log` |
| Traces | Span attrs `op` only | `_run` |
| Decision ledger / explain view | Yes, plaintext | `DecisionRecord.secret` |
| Wire errors | No | `to_wire` |

- `audit.py::pseudonymise(name, key)` returns `sn:` + 16 hex of HMAC-SHA256. Any export of audit or ledger data off-host MUST pseudonymise names with a key held outside the telemetry system. Wiring `pseudonymise` into an exporter is NOT IMPLEMENTED (no exporter exists).
- The explain view MUST be restricted to operators.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
