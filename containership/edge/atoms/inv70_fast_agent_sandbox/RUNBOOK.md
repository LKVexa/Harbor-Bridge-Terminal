# INV-70 operations runbook (C097, C056)

Paging target: **UNASSIGNED on-call alias** (OWNERS.md). Until one is named, pages go to the accountable owner.

## Severity
| Sev | Definition | Ack | Examples |
|---|---|---|---|
| SEV1 | Suspected isolation escape, audit chain broken or unavailable, sandbox HALT in prod | 15 min | FB-S022, `AuditLog.verify` false, HALT |
| SEV2 | Security denial spike, worker crash storm, breaker open > 10 min | 30 min | FB-S0xx ×5, FB-I001 |
| SEV3 | Sustained shedding > 5%, p99 SLO breach | next business hour | FB-C001, latency |
| SEV4 | Single-tenant degradation with a workaround | ticket | |

## Degraded modes
| Mode | Trigger | Behaviour | Exit |
|---|---|---|---|
| normal | — | everything on | — |
| reduced | overload with the breaker not closed | host calls off, fuel ×0.5 | shedding stops and the breaker closes |
| control-plane-degraded | control plane unreachable | serve on last known good config; `ConfigStore.frozen` | control plane reachable again |
| drain | operator sets `draining` | no new admissions (FB-C004); in-flight runs finish | operator clears it |
| halt | trust store, time source or audit sink lost | reject everything (FB-C003) | dependency restored and `audit.write_failures` reset after verification |

## Playbooks
- **halt:** find which of `trust.available`, `clock.healthy` or `audit.write_failures` is failing (`Sandbox.health()`). Restore it. Run `AuditLog.verify(entries, key, sealed_head)` before clearing. Do not bypass.
- **security-spike:** group by `reason_code` and tenant pseudonym. Revoke keys with `TrustStore.revoke(kid)`. Contain one tenant with a `per_tenant_concurrent=0` site overlay (audited activation).
- **worker-crash:** the breaker opens by itself. Check host memory and PID limits, then roll back the last config (`ConfigStore.rollback`).
- **overload:** confirm callers use `RetryPolicy`. Raise capacity through an overlay only with the reliability reviewer's approval.

## Recovery and post-incident
Roll back config first. Verify the audit chain. Write the post-incident review within 5 business days and add a regression test (see the checklist's "regression coverage" items).
