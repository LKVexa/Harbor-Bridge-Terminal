# INV-19 incident runbook (C097, MC-28)

Severity: **SEV1** data loss / cross-tenant exposure / all I/O stalled; **SEV2** fast path lost fleet-wide or error rate > 5%; **SEV3** single-node degradation. Paging per `OWNERSHIP.md` (currently UNASSIGNED → BLOCKED).

| Incident | Detect | Contain | Recover |
|---|---|---|---|
| Backend unavailable | `INV19BackendUnhealthy`; snapshot `health` | `AsyncHost.recover(reason)` (bounded) | failover to next priority; portable is always available |
| Persistent portable fallback | `INV19PersistentFallback`; `selection.rejected` reasons | none needed (safe) | fix reason code (e.g. `EPERM_SECCOMP_OR_SYSCTL` → container seccomp profile; `ADMIN_DISABLED` → sysctl `kernel.io_uring_disabled`) |
| Descriptor/handle exhaustion | `INV19QueueSaturation`; `QuotaExceeded.scope` | lower tenant quota (dynamic config) | identify tenant via pseudonym in audit; raise quota only via reviewed config |
| Completion latency spike | `INV19ReapP99` | check `inv19_queue_depth`, CPU | if one backend: quarantine it |
| Unknown native errors | `INV19UnknownHostErrors` | none; errors surface as UNKNOWN_HOST_ERROR (never success) | add mapping in `hostio/errors.py` + golden fixture + regression |
| Stalled backend | health DEGRADED; stall threshold `health.stall_s` | `recover()` | quarantine after `health.max_recoveries` |
| Audit exporter failure | `INV19AuditExportFailure` | security actions fail closed after buffer | restore sink; `AuditLog.flush()`; verify chain `verify_file` |
| Security isolation incident | `denials` in audit; cross-tenant attempts | revoke capability serial; rotate key | `KeyProvider.rotate`, revoke old key; review audit chain |
| Configuration failure | activation raises `ConfigError`; nothing applied | none needed (atomic) | `ConfigStore.rollback` |
| Dependency/runtime incompatibility | `tools/pk_core_preflight.py` BLOCKED; probe reasons | block rollout | pin/restore dependency; re-run gate |
