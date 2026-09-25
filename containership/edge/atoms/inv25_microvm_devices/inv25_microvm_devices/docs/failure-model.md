# Failure model and recovery semantics (work item 21 — C051–C060, C089)

| Failure | Detection | Behaviour | Test |
|---|---|---|---|
| pk_core missing / incompatible | `pk_bootstrap` | machine-readable error, exit 3; standalone modules unaffected | `CompatTest.test_bootstrap_*` |
| Policy engine down | `dependency_probe` | activation refused, `ready=false`, reads continue | `test_dependency_down_blocks_activation` |
| Runtime partial failure / backend missing | fixture | terminal `DEPENDENCY_UNAVAILABLE`, no substitution | `IntegrationContractTest` |
| Snapshot peer incompatible | fixture | restore rejected (`COMPATIBILITY_MISMATCH`) | `test_snapshot_restore_rejects_surface_change` |
| Clock / identity unavailable | `Verifier` | reject all credentials | `test_clock_failure_fails_closed` |
| Disk full / read-only (state) | `_persist` OSError | commit aborted before pointer swap, temp file removed, `config.activation_failed` audited | `test_crash_points_leave_old_state` |
| Audit sink down | `AuditLog.emit` | mutation refused, nothing changes, `ready=false` | `test_audit_sink_down_blocks_mutation` |
| Crash during staging/activation/rollback | injected at `before_audit`, `before_persist`, `before_rename` | on restart, exactly the prior committed state loads | same |
| Concurrent writers / split-brain | CAS on digest | one winner, others `CONCURRENT_MODIFICATION` | `ConcurrencyTest` |
| Network partition (remote control plane) | host service | same as dependency down; last-known-good serves | EXTERNAL (no remote mode here) |

Retryable vs terminal: see `docs/error-contract.md`. Backoff: exponential, base 200 ms, cap 30 s,
full jitter, max 6 attempts — implemented by callers (INV-25 performs no internal retries).
Degraded mode (C056): reads + `permits()` stay available from the last activated snapshot; mutations stop.
Failover (C055): not applicable to the single-writer reference store (W-0004).
Recovery objective: restart restores state in O(size of state file) — sub-second at ceiling.
Quarantine (C059): `emergency_disable`.
