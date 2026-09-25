# Error catalogue (GAP06-ERR/1) — generated

Codes are append-only. Clients must branch on `code`, not on HTTP status.

| Code | Category | Retryable | HTTP | Operator remediation |
|---|---|---|---|---|
| `E_MALFORMED_EVIDENCE` | malformed | no | 400 | fix client encoder; do not retry unchanged |
| `E_TRAILING_BYTES` | malformed | no | 400 | fix client encoder; do not retry unchanged |
| `E_BAD_MAGIC` | malformed | no | 400 | fix client encoder; do not retry unchanged |
| `E_SCHEMA` | malformed | no | 400 | fix client encoder; do not retry unchanged |
| `E_SIGNATURE` | authentication | no | 401 | check enrolled AK / trust anchors / CRLs |
| `E_UNKNOWN_KEY` | authentication | no | 401 | check enrolled AK / trust anchors / CRLs |
| `E_CERT_CHAIN` | authentication | no | 401 | check enrolled AK / trust anchors / CRLs |
| `E_CERT_REVOKED` | authentication | no | 401 | check enrolled AK / trust anchors / CRLs |
| `E_POP_FAILED` | authentication | no | 401 | check enrolled AK / trust anchors / CRLs |
| `E_NONCE_MISMATCH` | freshness | no | 409 | request a new challenge; check TrustedClock health |
| `E_REPLAY` | freshness | no | 409 | request a new challenge; check TrustedClock health |
| `E_CHALLENGE_EXPIRED` | freshness | yes | 409 | request a new challenge; check TrustedClock health |
| `E_UNISSUED_CHALLENGE` | freshness | no | 409 | request a new challenge; check TrustedClock health |
| `E_CLOCK_ROLLBACK` | freshness | no | 409 | request a new challenge; check TrustedClock health |
| `E_TPM_CLOCK_UNSAFE` | freshness | no | 409 | request a new challenge; check TrustedClock health |
| `E_TIME_UNTRUSTED` | freshness | yes | 503 | request a new challenge; check TrustedClock health |
| `E_PCR_MISMATCH` | measurement | no | 422 | run explain(); compare PCRs with active policy; quarantine runbook |
| `E_EVENTLOG_MISMATCH` | measurement | no | 422 | run explain(); compare PCRs with active policy; quarantine runbook |
| `E_MEASUREMENT_REJECTED` | measurement | no | 422 | run explain(); compare PCRs with active policy; quarantine runbook |
| `E_UNSUPPORTED_ALG` | unsupported | no | 422 | see COMPATIBILITY.md |
| `E_UNSUPPORTED_PLATFORM` | unsupported | no | 422 | see COMPATIBILITY.md |
| `E_TCB_OUT_OF_DATE` | tcb | no | 422 | update firmware/TCB |
| `E_DEBUG_ENABLED` | tcb | no | 422 | update firmware/TCB |
| `E_UNAUTHENTICATED` | authorization | no | 401 | check principal roles and scopes |
| `E_FORBIDDEN` | authorization | no | 403 | check principal roles and scopes |
| `E_TENANT_BOUNDARY` | authorization | no | 403 | check principal roles and scopes |
| `E_RATE_LIMITED` | capacity | yes | 429 | back off with jitter; honour retry_after |
| `E_OVERLOADED` | capacity | yes | 503 | back off with jitter; honour retry_after |
| `E_UNKNOWN_NODE` | state | no | 404 | check enrollment/policy state |
| `E_REVOKED` | state | no | 403 | check enrollment/policy state |
| `E_DUPLICATE_IDENTITY` | state | no | 409 | check enrollment/policy state |
| `E_CONFLICT` | state | yes | 409 | check enrollment/policy state |
| `E_POLICY_ROLLBACK` | state | no | 409 | check enrollment/policy state |
| `E_POLICY_UNSIGNED` | authentication | no | 401 | check enrolled AK / trust anchors / CRLs |
| `E_QUORUM` | authorization | no | 403 | check principal roles and scopes |
| `E_FENCED` | state | yes | 409 | check enrollment/policy state |
| `E_LEDGER_TAMPER` | internal | no | 500 | page on-call; preserve evidence |
| `E_STATE_CORRUPT` | internal | no | 500 | page on-call; preserve evidence |
| `E_INTERNAL` | internal | yes | 500 | page on-call; preserve evidence |
