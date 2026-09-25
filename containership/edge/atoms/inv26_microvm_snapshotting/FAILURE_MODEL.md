# Failure model (C051-C060)

| # | Failure | Detection | Behaviour | Evidence |
|---|---|---|---|---|
| F01 | service process crash mid-capture | restart → `reconcile()` | record retired FAILED, blob GC'd, id retryable | faults crash_matrix capture k=1..5 |
| F02 | crash mid-restore | restart → `reconcile()` | grant FAILED (retryable), guest killed with process (jailer) | faults crash_matrix restore k=1..4 |
| F03 | torn metadata write | WAL checksum | discarded (never acknowledged) | test_crash_during_activation_is_all_or_nothing |
| F04 | VMM API error / socket gone | HTTP status / OSError | `SNAP_HYPERVISOR_FAILED`, retried if budget, guest destroyed | test_adapters, faults hypervisor_* |
| F05 | VMM hang | socket timeout | `SNAP_TIMEOUT` | hypervisor._call timeout |
| F06 | guest agent absent/lying | proof mismatch | `SNAP_ENTROPY_FAILED`, guest destroyed, never resumed | test_adapters lying/refusing agent |
| F07 | KMS outage / key disabled | port error | fail closed; not ready | faults kms_down, key_disabled |
| F08 | storage outage / full / corrupt | OSError / ENOSPC / digest+AEAD | retryable / STORAGE_FULL / integrity rejection + scrub quarantine | faults storage_down, test_scrub |
| F09 | audit sink down | append OSError | bounded buffer; privileged ops fail closed | test_privileged_ops_fail_closed_without_audit |
| F10 | overload / noisy neighbour | admission | `SNAP_OVERLOADED` + retry_after before work | test_rate_limit_and_fairness, test_admission_ceiling_holds |
| F11 | dependency flapping | circuit breaker | open after N retryable failures, half-open probe | faults breaker |
| F12 | split brain / paused controller | lease + fencing token | `SNAP_FENCED` for stale writer | test_stale_controller_is_fenced |
| F13 | duplicate request / replay | idempotency key, grant nonce | recorded result or `SNAP_GRANT_REPLAYED` | AntiReplay tests, concurrency |
| F14 | stuck operation | `stalled()` vs `lifecycle.STATE_TIMEOUT_S` | gauge + INV26-Stalled alert | service.stalled |
| F15 | node loss | — | snapshots are node-local on the filesystem adapter; **no failover** (replication prohibited). Restore elsewhere requires shared storage + residency approval — not provided | C055 PARTIAL |
| F16 | site/region loss | — | same as F15 | C055 PARTIAL |

**Health/stall thresholds (C052):** readiness false when any critical dependency (kms, storage, hypervisor,
metadata) probe fails, when emergency-disabled, or with no active config; stall = in-flight op older than
its state budget (capture 120 s, restore 10 s).

**Retry (C053):** only catalog-retryable codes, full-jitter backoff, per-call attempt cap, shared budget
(ratio 0.2), never past the deadline. **Degraded mode (C056):** telemetry and audit-buffering are the only
degradable dependencies. **Quarantine/disable (C059):** per-snapshot quarantine, automatic integrity
quarantine by scrub, fleet-wide emergency disable. **Fault injection (C060):** `tools/faults.py`
(crash at every durable write for capture and restore, 8 dependency scenarios, breaker) → `evidence/FAULTS.json`.
