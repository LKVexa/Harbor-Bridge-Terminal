# Troubleshooting

| ID | INV55-OPS-TROUBLE | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Symptom | Likely cause | Check / fix |
|---|---|---|
| All requests `INV55-E013-FROZEN` | state not ready/degraded (starting, frozen, quarantined) | `health()["state"]`, `state_reason`; call `start()` or `unfreeze` |
| `quarantined` right after start | no active config | `ConfigController.activate` then freeze→unfreeze |
| Every resolve DENIED after restart | no `state_path` / state file missing; or policy rules not reloaded | check `<audit>.state.json`; `PolicyEngine.replace`; `set_scope` |
| `quarantined`, reason `audit_chain_divergence` | audit file failed verification at boot | incident-response.md §3 |
| `E999-INTERNAL` | unexpected exception, or state-file write failure on scope/retire (nothing applied) | `inv55_internal_errors_total{kind}`, `internal_error` log; fix disk; retry |
| Policy change not taking effect / wrong `policy_digest` | `.rules` mutated directly | use `PolicyEngine.replace` |
| High p99 under load | GIL/RLock contention | scale out processes (capacity-model.md) |
| `E015` on correct version | protocol family doesn't match operation | use `PK_SECRET_ROTATE/1` for rotate/retire, `PK_SECRET_SCOPE/1` for scope |
| DENIED for existing secret | missing role/rule/scope, or provider 404/403 | `DecisionLedger.explain(request_id)["why"]`; `inv55_denials_total{reason}` |
| `E014-AUDIT-UNAVAILABLE` | audit disk full/permission | fix sink; `inv55_audit_failures_total` |
| `E008-CLOCK-ROLLBACK` | injected clock went backwards / NaN | fix clock source; restart |
| `E009-PROVIDER-UNAVAILABLE` | Vault down/sealed, circuit open, TLS error | `health()["dependencies"]`; circuit resets after 5 s cooldown |
| `E005-CONTEXT-MISMATCH` on use | lease from other instance, restart, wrong name/subject | re-resolve; ensure sticky routing |
| `E019-CONFLICT` on rotate | CAS conflict | re-read version, retry with new `expected_version` |
| `E011-QUOTA-EXCEEDED` | authenticated tenant/workload bucket or 1 000 leases per subject | reduce rate; leases free on expiry |
| `rotate` returns `replayed: true` unexpectedly | idempotency key reused for the same tenant/name | use a fresh key |
| health `stalled: true` | requests in flight with no progress 30 s | inspect provider latency; restart |

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Write-ahead, policy replace, contention |
| 4.3.0 | 2026-09-22 | New codes and failure causes |
