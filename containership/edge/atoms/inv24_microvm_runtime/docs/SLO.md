# Production SLOs and support policy (MC-056)

| SLO | Objective | Window | Error budget | Burn-rate page | Measured by |
|---|---|---|---|---|---|
| Device model | 0 out-of-model boots | 30 d | none — any event is SEV1 | immediate | `microvm_device_refusals_total` + audit |
| Cold boot | p99 < 125 ms | 30 d | 1 % of boots | 14.4× over 1 h / 6× over 6 h | `microvm_boot_seconds` |
| Tenant isolation | 0 cross-tenant reuse | 30 d | none | immediate | ownership registry audit |
| Admission availability | 99.9 % non-5xx-equivalent decisions (excl. policy rejections) | 30 d | 43 min | 14.4× / 6× | `microvm_admission_decisions_total` |

Support: SEV1 24×7, SEV2 business-hours+on-call, SEV3 next business day. Owner of the policy: UNASSIGNED (BLOCKED).
