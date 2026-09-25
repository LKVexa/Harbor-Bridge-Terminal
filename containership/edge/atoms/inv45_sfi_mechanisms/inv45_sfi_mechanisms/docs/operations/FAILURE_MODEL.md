# Failure model, health/stall detection, failover and recovery (C051, C052, C055–C058, C060, C089)

## Failure modes

| Id | Failure | Detection | Containment | Recovery | Test |
|---|---|---|---|---|---|
| FM01 | Crash during config activation | CURRENT pointer unchanged / generation exists | lock + write-generation-then-swap-pointer | restart: previous generation active, or new one complete | `FM01_ConfigCrashDuringActivation` |
| FM02 | Corrupted active generation (bit-rot, tamper) | digest mismatch at read | refuse to use | `GenerationStore.recover` auto-rollback to newest valid generation, audit | `FM02_CorruptedActiveGeneration` |
| FM03 | Audit sink outage | write `OSError` | bounded spool; health `degraded`; fail closed when spool full | flush on recovery, chain intact | `FM03_AuditSinkOutage` |
| FM04 | Key/secret service unavailable | `SFI_DEPENDENCY_UNAVAILABLE` | no trust granted | automatic on reconnect | `FM04_KeyServiceUnavailable` |
| FM05 | Controller process crash/restart | process supervisor | durable state is atomic-write; instances are ephemeral | restart restores floors, quarantine, config, audit chain; no instance resurrected | `FM05_ControllerCrashAndRestart` |
| FM06 | Control-plane partition | freshness age | cached trust until `trust_max_age_seconds`, then `SFI_TRUST_STALE` | refresh on reconnect, no restart | `FM06_PartitionFromControlPlane` |
| FM07 | Engine unavailable / crashing | subprocess error, circuit breaker | execute fails closed; breaker opens after 3 failures | half-open after 30 s | `ServiceEndToEnd.test_engine_unavailable_fails_closed_and_breaker_opens` |
| FM08 | Runaway guest | per-job timeout | process killed | next job uses a fresh process | `test_runaway_execution_is_killed` |
| FM09 | Overload | admission queue/wait | shed with retryable `SFI_OVERLOADED` | client backoff | `ControlsTest.test_admission_quotas`, `test_admission_never_exceeds_caps` |
| FM10 | Two controllers on one state root (split-brain) | OWNER lock + fencing epoch | second controller refused; forced takeover fences the old one | operator takeover procedure | `ControlsTest.test_durable_state_quarantine_floors_and_fencing` |
| FM11 | Duplicate load of one descriptor | replay cache | exactly one succeeds | — | `test_descriptor_replay_race_exactly_one_load` |
| FM12 | Stale activation lock after a hard kill (SIGKILL during activation) | activations fail with `SFI_CONFIG_CONFLICT` "in progress" | no partial generation is active | operator removes `.activate.lock` after confirming no writer (RUNBOOKS.md §Day-2) | none (manual; waiver W-06) |
| FM13 | Node, VM, site or provider loss | external orchestrator | the component holds no cross-node state; each node is independent | redeploy (day-0) + restore state root (BACKUP_RESTORE.md) | external |

Node/VM/site/provider/network failures beyond FM06/FM13 are outside this component: it has no replication,
no leader election and no cross-node state. **Failover** therefore means "another node with its own state
root takes new work"; it cannot violate isolation because descriptors are node-local (sealing key shared
only if the operator shares it) and anti-rollback floors must be seeded from backup before a node takes
traffic (BACKUP_RESTORE.md).

## Degraded operation (C056)

Non-critical: audit sink (spooled), metrics/log export, engine for *other* tenants' execute (breaker).
Critical (fail closed, no degraded mode): key service, IdP, config store, verifier.

## Crash consistency, replay, duplicate execution (C057, C058)

* Config and state writes: temp + fsync + rename; immutable generations created with `link` (never
  overwritten); activation under an exclusive lock with compare-and-swap on the current generation.
* Audit: sequence + hash chain; restart continues from the last event.
* Descriptors: one-time nonce, so a retried load after a crash cannot load twice (the retry fails
  `SFI_REPLAY_DETECTED`; resubmit for a fresh descriptor).
* Execute jobs are not resumable; a crashed job is reported failed and must be re-invoked by the caller.

## Health and stall thresholds (C052)

| Signal | Threshold | State |
|---|---|---|
| `health().status` | `ready` | alive + ready |
| key freshness age > `trust_max_age_seconds` | immediate | `dependency_stale`, not ready |
| no active sealing key | immediate | `degraded` |
| audit spool > 0 | immediate | `degraded`; alert if > 60 s |
| engine breaker open | immediate | `degraded` |
| global quarantine present | immediate | `quarantined` |
| stall: admission `waiting > 0` and no completions for 30 s | 30 s | alert `INV45Stalled` |
| verify p95 > 2× baseline for 10 min | 10 min | alert `INV45VerifyLatency` |

Detection objectives: dependency loss visible in health within one call; stalls alerted within 1 min
(rules in `ops/alerts/inv45-rules.yml`, not yet exercised against a live Prometheus — open).
