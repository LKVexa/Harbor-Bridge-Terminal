# System failure-mode matrix (C051) and degraded modes (C056)

| Failure | Detection | Behaviour | Recovery | Test |
|---|---|---|---|---|
| Consumer crash holding a lease | deadline passes | redeliver (new token) or dead-letter at cap | automatic | contract tests |
| Poison message | attempts == max | dead-letter with reason | operator redrive/purge | `test_dead_letter_redrive_and_purge_are_durable` |
| Disk write error / full | OSError on write/fsync | fail-stop, `E_STORAGE`, breaker counts | reopen + replay; breaker half-open probe | `test_storage_failure_opens_breaker…` |
| Crash mid-append | torn final line | truncated on open | automatic | `test_torn_final_record…` |
| Crash after durable write | record present, memory lost | replay applies it | automatic | `test_crash_after_write…`, crash-anywhere property |
| Crash during compaction | journal records ≤ snapshot seq | skipped on replay | automatic | `test_crash_between_snapshot_and_journal_reset_recovers` |
| Journal tail removed | clean marker / anchor mismatch | refuse to open | restore from backup | `test_tail_removal_after_clean_shutdown_is_detected` |
| Journal/snapshot corruption | chain/digest mismatch | refuse to open; queue frozen `E_CORRUPT` | restore from backup | corruption tests |
| Second writer | OS lock | `OwnershipError` | wait for owner exit | `test_second_live_writer_is_refused` |
| Superseded writer (shared storage) | epoch mismatch | `E_EPOCH_FENCED` | node stands down | `test_epoch_fencing…` |
| Key provider outage | provider exception | `E_SECURITY_DEPENDENCY` (fail closed) | restore provider | `test_kms_unbound_fails_closed` |
| Audit sink outage | append/open error | `E_SECURITY_DEPENDENCY` | restore sink | `test_T7_…` |
| Overload | ready ≥ watermark | shed puts, keep consumers | drains naturally | `test_quota_and_shedding` |
| Stall (no settlement while work is ready) | `stall_seconds` | health `ready=false`, queue `stalled=true` | investigate consumers | `test_health_readiness_and_stall_detection` |

## Degraded operating modes (reported as `health().mode`)
| Mode | Entered when | Admitted | Refused |
|---|---|---|---|
| NORMAL | default | everything authorised | — |
| DEGRADED_SHEDDING | any queue ready ≥ `shed_ready_ratio × max_ready` | consumers, puts to other queues | puts to the hot queue (`E_SHED`) |
| DEGRADED_STORAGE | any queue breaker open/half-open | ops on healthy queues; one probe on the failing queue | writes to the failing queue (`E_CIRCUIT_OPEN`) |
| DRAINING | `drain()` | consumers | puts (`E_DRAINING`) |
| DISABLED | `emergency_disable()` | health via in-process call | all data-plane ops (`E_FROZEN`) |
Readiness is true only in NORMAL or DEGRADED_SHEDDING with no stalled queue.
