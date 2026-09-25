# Fault catalog (MC-044)

| Fault | Injection | Safety invariant | Recovery expectation | Test |
|---|---|---|---|---|
| Process crash before/mid/after WAL write, before/after fsync | `wal` fault hooks raising `SimulatedCrash` | acknowledged writes present; unacked write atomic | restart recovers, torn tail truncated | `test_durability.test_crash_at_every_persistence_boundary` |
| Crash during snapshot rename | fault hook | previous generation authoritative | restart recovers | `test_crash_during_snapshot` |
| Disk full (ENOSPC), I/O error (EIO) | fault hook raising `OSError` | no ack, fail closed | operator frees space/replaces disk, restarts | `test_io_error_fails_closed_and_never_acks` |
| Bit rot mid-WAL / snapshot / ciphertext | byte flips | never serve ambiguous state | restore from backup | corruption tests |
| Stall / deadlock | hold store lock | liveness reports `stalled` | orchestrator restarts | `test_liveness_detects_stall` |
| Slow consumer / watch overload | fill queues | no silent event loss | fallback or explicit cancel | watch tests |
| Overload / request flood | token bucket, in-flight gate | shed load with retry-after | clients back off | quota tests |
| Network interruption / reconnect | server shutdown during watch | resume without loss | client resumes/relists | `test_http.*drain*`, mirror test |
| Compaction racing consumers | compact during catch-up/mirror | explicit COMPACTED → relist | mirror converges | watch + mirror tests |
| Replication gap / stale epoch | out-of-order / old-epoch batches | no divergent apply | resync from snapshot | `test_backup_repl` |
| Randomised fault schedule | seeded random crash points over 200 ops | as above | as above | `test_chaos.RandomScheduleTest` |

Containment of chaos tooling (MC-044-06): fault hooks are constructor parameters only (no global switch, no env var), default to no-ops, and exist only on `DurableStore`/`WriteAheadLog`; tests use temporary directories.
