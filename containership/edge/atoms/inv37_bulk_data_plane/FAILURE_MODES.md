# INV-37 failure modes, detection and recovery

**Version:** 4.3.0 · Covers INV-37-C051, C052, C055–C060, C089.

| # | Failure | Scope | Detection | Behaviour | Recovery objective | Test |
|---|---|---|---|---|---|---|
| F01 | Chunk corrupted in transit | chunk | digest mismatch | reject chunk, `digest_mismatch_total{level=chunk}`; transfer continues | re-send chunk | test_integration `corrupt_chunk_then_resend` |
| F02 | Object corrupt after all chunks (region/disk mutated) | transfer | final re-verify | `QUARANTINED`, slot released, audit | integrity incident; never delivered | `final_verification_failure_quarantines`, test_transport |
| F03 | Producer stalls / peer disconnect | transfer | `sweep()` idle > `timeouts.idle_chunk` | `DISCONNECTED`, decision `stall_detect` | resume on next chunk or `reconcile` | `stall_detection_and_total_timeout` |
| F04 | Transfer exceeds total time | transfer | `sweep()` > `timeouts.total_transfer` | `FAILED_TERMINAL`, resources released, checkpoint kept for inspection | operator GC | same |
| F05 | Process crash mid-write | process | restart | `recover()` reloads sealed state; unacked chunk missing | RPO 0 acked chunks; RTO = recover time | test_checkpoint `crash_during_write_sequence`, `restart_resume` |
| F06 | Checkpoint tampered / torn | node disk | seal / re-hash | quarantine or drop chunk | re-send dropped chunks | `broken_seal_quarantines`, `corrupt_data_is_dropped` |
| F07 | Checkpoint I/O error (EIO/ENOSPC) | node | OSError | `FAILED_RETRYABLE`, `timeout` (retryable), health `degraded` | retry succeeds when storage recovers | `checkpoint_io_failure_is_retryable` |
| F08 | Storage quota exhausted | node | store accounting | `quota_exceeded` at create | GC / raise quota | test_checkpoint `storage_quota` |
| F09 | Duplicate owner / stale node (split brain) | cluster | lease epoch | `stale_owner` on write | newer epoch owns | `fencing_split_brain` |
| F10 | Overload | node | admission | `admission_rejected`/`quota_exceeded` + reason; no cascade | clients back off (RetryPolicy) | test_quota, bench burst profile |
| F11 | Telemetry export failure | dependency (non-critical) | export error counter | transfers continue, health `degraded` | fix sink | `degraded_telemetry_does_not_block` |
| F12 | Time source failure | dependency (critical) | clock raises | authentication fails closed | restore time | test_security |
| F13 | Key ring missing / bad perms | dependency (critical) | preflight | admission disabled | fix key file | test_config, test_bootstrap |
| F14 | Shared memory unavailable | platform | probe | auto → copy (degraded); required → fail closed | — | test_transport, test_config |
| F15 | Config bad after change | control | health check | automatic rollback | previous config active | `test_activation_rollback` |
| F16 | Unsafe behaviour detected | transfer/tenant/node | operator/auto | quarantine transfer or tenant, freeze admission | `release`, unfreeze | `operator_controls` |
| F17 | VM / node loss | node | external orchestrator | in-flight transfers on that node stop; durable state on local disk | restart on same disk → `recover()`; different node → re-transfer from source | — (external drill) |
| F18 | Site / provider / network partition | site | external | no cross-site state; each site independent | re-transfer or wait | — (external drill) |
| F19 | Control-plane loss | dependency | manifests not arriving | existing transfers continue (local authn); no new manifests | — | — (external drill) |

## Failover (C055)

INV-37 has no cross-node state replication, so failover = **ownership takeover** of a checkpoint directory on shared or re-attached storage: the new node calls `acquire()` (epoch+1) via `recover()`; the old node is fenced. Takeover must not cross residency (`security.allowed_regions`) or tenant region lists; policy precedence forbids moving state to a non-permitted region even if faster. Checkpoints never leave the configured directory.

## Degraded operation (C056)

| Dependency | Critical? | Degraded behaviour |
|---|---|---|
| Telemetry export | no | continue; health `degraded` |
| Shared memory | no (auto) | copy path; health reason via finding `copy_fallback` |
| Checkpoint storage | yes on prod/edge | per-transfer retryable failure; admission continues for other transfers |
| Clock, key ring | yes | fail closed |
| pk_core | no | governance tests NOT_EXECUTED |

## Fault injection (C060)

In-repo fault injection covers F02, F03, F04, F05 (process kill at both write-ordering boundaries), F06, F07 (injected EIO), F09, F10, F11, F12. Node/VM loss, partitions, provider outage and degraded control plane (F17–F19) need a real topology and are the gate criterion `partition_disaster_drill`.
