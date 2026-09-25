# Interface limits, capacity ceilings, quotas and fairness (MC-008 / MC-018 / MC-072)

All values are defaults in `config.DEFAULTS` / `control.Limits`; numbers are **PROPOSED** pending owner approval.

| Limit | Value | Enforced in | On breach |
|---|---|---|---|
| Concurrent sandboxes per node | 256 | `Admission.acquire` | E_OVERLOADED (retryable) |
| Concurrent sandboxes per tenant | 32 | `Admission.acquire` | E_QUOTA_EXCEEDED (retryable) |
| Control payload size | 64 KiB | `Admission.check_payload` | E_LIMIT_EXCEEDED |
| Config document size | 256 KiB | `config.load` | E_CONFIG_INVALID |
| Profile items per list | 4096 | `sandbox._normalise_tokens` | ProfileInvalid |
| Syscall allow-list | budget 60 (tighten-only), compiler max 1024 | runtime, `seccomp.compile_filter` | E_PROFILE_INVALID |
| Token size / TTL | 4 KiB / 1 h | `control.authenticate` | E_UNAUTHENTICATED |
| Nonce cache | 100 000 | `EvidenceVerifier` | E_OVERLOADED |
| Metric series | 2048 | `Metrics` | dropped + counted |
| Audit event | 16 KiB | `AuditChain.append` | digested |
| Idempotency cache | 10 000 keys / 1 h | `IdempotencyCache` | oldest 10% evicted |
| Per-sandbox rlimits | core 0, nofile 256, nproc 256, fsize 64 MiB | launcher | kernel enforcement |
| Launch readiness timeout | 10 s | launcher | E_TIMEOUT |
| Workload timeout | 30 s default, ≤ 24 h | launcher | tree killed |

Fairness: per-tenant quota is a hard cap; there is no queue in 5.1.0 (max_queue is reserved), so excess work is shed with a retryable code and callers back off with `control.retry` (full jitter).

Capacity model (MC-072): measured on the test node, one launcher thread sustains ~73 sequential launches/s at 2.2 ms host CPU each (`evidence/bench-*.json`). Saturation signals: `inv39_admission_rejections_total`, `inv39_launch_seconds` p99, node `nproc` headroom. Fleet-level model: BLOCKED (no fleet data).
