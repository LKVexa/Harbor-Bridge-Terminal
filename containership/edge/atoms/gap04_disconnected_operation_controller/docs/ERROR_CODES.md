# GAP-04 Error Codes (`PK_GAP04_ERROR/1`)

Generated from `runtime/errors.py`. Codes are append-only; meaning never changes within a major error-model version. Human messages may be localized; `code` is the only contract.

| Code | Category | Retryable | HTTP | Meaning | Operator remediation |
|---|---|---|---|---|---|
| GAP04-E0001 | lifecycle | no | 409 | operation requires an active partition | Follow the lifecycle order: partition → decide → reconnect(reconcile) → install lease/policy. |
| GAP04-E0002 | lifecycle | no | 409 | reconciliation required before this operation | Follow the lifecycle order: partition → decide → reconnect(reconcile) → install lease/policy. |
| GAP04-E0003 | lifecycle | no | 400 | timestamp predates last state-changing event | Follow the lifecycle order: partition → decide → reconnect(reconcile) → install lease/policy. |
| GAP04-E0004 | validation | no | 400 | input failed validation | Fix the request; do not retry unchanged. |
| GAP04-E0100 | authority | no | 403 | autonomy lease expired or absent | Expected fail-closed outcome. Restore connectivity / obtain a new lease or policy; never bypass. |
| GAP04-E0101 | authority | no | 403 | action not permitted at current tier | Expected fail-closed outcome. Restore connectivity / obtain a new lease or policy; never bypass. |
| GAP04-E0102 | authority | no | 403 | cached policy exceeds staleness bound | Expected fail-closed outcome. Restore connectivity / obtain a new lease or policy; never bypass. |
| GAP04-E0103 | authority | no | 403 | controller quarantined / emergency disabled | Expected fail-closed outcome. Restore connectivity / obtain a new lease or policy; never bypass. |
| GAP04-E0104 | authority | no | 403 | caller not authorized for this boundary | Expected fail-closed outcome. Restore connectivity / obtain a new lease or policy; never bypass. |
| GAP04-E0105 | authority | no | 403 | capability grant missing, revoked, or insufficient | Expected fail-closed outcome. Restore connectivity / obtain a new lease or policy; never bypass. |
| GAP04-E0200 | crypto | no | 401 | lease envelope malformed or non-canonical | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0201 | crypto | no | 401 | lease signature invalid | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0202 | crypto | no | 401 | unknown or revoked issuer / key id | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0203 | crypto | no | 401 | algorithm not in allow-list | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0204 | crypto | no | 401 | lease scope/binding mismatch | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0205 | crypto | no | 401 | lease time validity failure | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0206 | crypto | no | 401 | lease authority epoch stale or revoked | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0207 | crypto | no | 401 | lease policy digest mismatch | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0208 | crypto | no | 503 | trust store unavailable or crypto backend missing | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0209 | crypto | no | 401 | unsupported envelope version | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0210 | crypto | no | 401 | lease replay (nonce / lease id reused) | Security signal. Check issuer, trust bundle version, and clock; see RUNBOOK RB-07. |
| GAP04-E0220 | policy | no | 401 | policy bundle signature/digest invalid | Issuer must publish a correctly signed, higher policy_version. |
| GAP04-E0221 | policy | no | 409 | policy rollback / version not monotonic | Issuer must publish a correctly signed, higher policy_version. |
| GAP04-E0300 | time | no | 503 | trusted time unavailable or rollback detected | Anchor trusted time (signed token/NTS); never roll the clock. RB-07. |
| GAP04-E0400 | storage | no | 507 | durable journal cannot append (capacity) | RB-05 (capacity) or RB-09 (integrity). Do not delete journal files. |
| GAP04-E0401 | storage | no | 500 | journal corruption detected | RB-05 (capacity) or RB-09 (integrity). Do not delete journal files. |
| GAP04-E0402 | storage | no | 500 | audit chain integrity failure | RB-05 (capacity) or RB-09 (integrity). Do not delete journal files. |
| GAP04-E0403 | storage | no | 500 | state store integrity / decryption failure | RB-05 (capacity) or RB-09 (integrity). Do not delete journal files. |
| GAP04-E0404 | storage | no | 409 | state schema version unsupported | RB-05 (capacity) or RB-09 (integrity). Do not delete journal files. |
| GAP04-E0500 | fencing | no | 409 | stale controller generation (fenced) | A newer controller owns the state; stop this instance. |
| GAP04-E0501 | fencing | yes | 409 | another controller instance holds the ownership lock | A newer controller owns the state; stop this instance. |
| GAP04-E0600 | reconcile | yes | 502 | reconciliation peer failure | Retry reconnect(); progress is persisted. RB-06. |
| GAP04-E0601 | reconcile | no | 409 | reconciliation transaction id conflict | Retry reconnect(); progress is persisted. RB-06. |
| GAP04-E0700 | overload | yes | 429 | admission rejected: queue or concurrency limit | Back off with jitter and retry. RB-10. |
| GAP04-E0701 | overload | yes | 503 | circuit open for dependency | Back off with jitter and retry. RB-10. |
| GAP04-E0800 | config | no | 400 | configuration invalid | Fix configuration / obtain distinct approver. |
| GAP04-E0801 | config | no | 409 | configuration activation conflict / rollback unavailable | Fix configuration / obtain distinct approver. |
| GAP04-E0802 | config | no | 403 | override lacks required approvals | Fix configuration / obtain distinct approver. |
| GAP04-E0900 | adapter | yes | 502 | adjacent-layer adapter failure | Check adjacent component health and contract version. |
| GAP04-E0901 | adapter | no | 409 | adjacent-layer contract version unsupported | Check adjacent component health and contract version. |
