# INV-63 Failure Matrix

| Field | Value |
|---|---|
| Document ID | INV63-ARCH-FAILURE-MATRIX |
| INV-63 C-IDs covered | C051, C052, C053, C054, C055, C056, C057, C058, C059, C060 (also C048, C089) |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role), Architecture reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change. |

Fault tests use `adapter.InMemoryLattice` (fields `partitioned`, `fail_start`, `fail_hosts`, `unhealthy_versions`). No test ran against real Wadm, real nodes or real sites; no game day has been run.

| Failure | Detection | Response | Outcome / error code | Recovery | Test |
|---|---|---|---|---|---|
| Component start failure | `adapter.start` raises | retry (idempotent, bounded `retry_max_attempts`), breaker; same-version stops skipped to keep capacity | `PARTIAL`, lifecycle `DEGRADED`, per-instance codes (e.g. `INV63-E-DEPENDENCY-UNAVAILABLE`) | next `tick()`/reconcile retries | `test_service.py::SemanticsTest::test_partial_outcome_when_some_starts_fail` |
| New version unhealthy in rollout | `adapter.healthy(ni)` False | `ROLLING_BACK`, `_rollback` restores old instances | `INV63-E-ROLLOUT-FAILED` (TERMINAL) with `cause`, `restored` | automatic; operator re-rolls after fix | `test_service.py::RolloutTest::test_failed_rollout_rolls_back_automatically` |
| Rollback itself fails | `_rollback` raises | lifecycle `ROLLING_BACK → FAILED`, metric `rollbacks{kind="failed"}` | `INV63-E-ROLLOUT-FAILED`, `details.state="FAILED"`, `cause`, `rollback_error` | operator (`INCIDENT.md`); `set_desired` returns to `VALIDATED` | `tests/test_service.py::RolloutTest` |
| Process crash | restart | `_recover` replays journal (leading `snapshot` if compacted, then desired, lifecycle, controls, host quarantine, emergency disable, offline intents, idempotency); torn tail truncated | none if chain valid | automatic on start; `epoch` re-acquired only if 0 in this handle | `test_service.py::DurabilityTest::test_crash_replay_restores_desired_lifecycle_controls` |
| Stall (no progress) | `HealthMonitor.stalled()` > `stall_threshold_s` (120 s default) | `tick()` sets `stalled_workloads` gauge; alert `INV63Stalled` (SEV2, page) | status `stalled` list | operator (DAY2/INCIDENT runbooks) | `test_service.py::HealthTest::test_stall_detection` |
| VM / node loss (manager host) | external (process gone) | another instance must `Journal.acquire()` on the same `state_dir` | old leader fenced `INV63-E-STALE-EPOCH` | restore/attach state dir; automatic failover **not implemented**; fencing single-host only (DEBT-001) | `test_service.py::DurabilityTest::test_stale_controller_is_fenced` |
| Lattice host (node) bad | operator decision | `quarantine_host(host, True, principal)` (platform principal, `control:quarantine`) excludes host in `_eligible`; next reconcile moves instances off | normal reconcile outcomes | `quarantine_host(host, False, principal)` | `test_service.py::ControlsTest::test_host_quarantine_drains_node` |
| Lattice host disappears | `_observe` drops instances on unknown hosts only; missing instances appear as a diff | restart on remaining eligible hosts | `SUCCESS`/`PARTIAL` | automatic | covered indirectly by `test_partial_outcome_when_some_starts_fail` |
| Site loss | external | none in code; each site has its own instance/journal | n/a | restore from backup (BACKUP_RESTORE.md) | none — open |
| Network partition (to lattice) | `list_instances` raises `INV63-E-CONTROL-PLANE-OFFLINE` / breaker open | offline mode: journal `offline_intent`, `DEGRADED`; rollouts refused | `DEGRADED` within `offline_autonomy_s`; beyond: `INV63-E-CONTROL-PLANE-OFFLINE` (RETRYABLE) | `resync()` after reconnect (automatic in `tick()` when intents are pending) | `test_service.py::SemanticsTest::test_offline_mode_queues_intent_then_resyncs`, `::test_offline_beyond_autonomy_window_is_retryable_failure` |
| Provider failure | not modelled (providers not owned, `contract.py` not_owns) | — | — | — | none |
| Dependency: crypto missing | `HAVE_CRYPTO` False; preflight A-07 | `_require_crypto` fails closed | `INV63-E-DEPENDENCY-UNAVAILABLE`; not ready | install pinned `cryptography==46.0.7` | `test_security.py::ArtifactTest::test_verifier_unavailable_fails_closed` |
| Dependency: artifact verifier absent | `verifier is None` | fail closed | `INV63-E-DEPENDENCY-UNAVAILABLE` | inject verifier | same as above |
| Dependency: secret ref missing | `resolve_secret_ref` | fail closed | `INV63-E-DEPENDENCY-UNAVAILABLE` | provision secret | `test_security.py::SecretsAndCryptoTest::test_secret_refs` |
| Control plane (Wadm/lattice) flapping | `CircuitBreaker` after `circuit_failure_threshold` (5) retryable failures | calls short-circuit for 10 s, then half-open | `INV63-E-CIRCUIT-OPEN` (RETRYABLE, `retry_after_s`) | automatic half-open probe | `test_platform.py::ResilienceTest::test_circuit_breaker`, `::test_fault_injection_breaker_trips_and_recovers` |
| Overload | `Admission.enter` | shed batch >80%, reject >`max_inflight` (critical exempt), tenant bucket | `INV63-E-OVERLOADED` / `INV63-E-QUOTA` with `retry_after_s` | client backoff | `test_platform.py::ResilienceTest::test_admission_shedding_and_quota` |
| Deadline | `Deadline.check` / retry budget | abort remaining actions | `INV63-E-DEADLINE` (RETRYABLE); committed actions remain journaled | retry same idempotency key | `test_service.py::IdempotencyTest::test_deadline_exceeded` |
| Journal disk: torn write | `_load`: last line without newline | truncate + fsync; `recovered_torn_tail=True` logged | none | automatic | `test_service.py::DurabilityTest::test_crash_replay_restores_desired_lifecycle_controls` (torn tail) |
| Journal disk: mid-file corruption | `_load` chain/JSON check | refuse to start | `INV63-E-STATE-CORRUPT` | restore from backup | `test_service.py::DurabilityTest::test_mid_journal_corruption_refuses_start` |
| Journal disk: full / unwritable | `OSError` in append; preflight A-04 | request fails | `INV63-E-DEPENDENCY-UNAVAILABLE` via `errors.classify` | free space / new disk + restore | none — open |
| Journal size limit | `size > max_bytes` (256 MiB) | refuse append | `INV63-E-QUOTA` | backup, then `DeploymentService.compact()` (one `snapshot` record, atomic `os.replace`); not automatic | see compaction tests in `tests/test_service.py` |
| Concurrent writer | file size != expected | refuse append | `INV63-E-CONFLICT` | single writer | `test_platform.py::ConcurrencyTest::test_two_handles_cannot_interleave_journal_writes` |
| Clock skew | preflight A-05 (only with a `reference_time`); token nbf/exp ± 30 s | not ready / token rejected | `INV63-E-PRECONDITION` / `INV63-E-UNAUTHENTICATED` | fix NTP | none specific for A-05 |
| Clock jump (wall) | none | autonomy window uses the monotonic clock (`mono`), unaffected; token nbf/exp and preflight A-05 use wall time | `INV63-E-UNAUTHENTICATED` on large jumps | fix NTP | none specific |

Operator containment (C059): `freeze`/`quarantine` request ops (workload or `tenant/*`), `quarantine_host`, `emergency_disable` — all journaled and replayed; `reconcile_ns` and `op_rollback` call `controls.check`, so no lattice action runs under a control; `tests/test_service.py::ControlsTest::test_freeze_quarantine_and_emergency_disable`.

Recovery objectives (RTO/RPO) are not defined numerically in code; proposed RPO = 0 for acknowledged requests (fsync per record, A-12), RTO = process restart + replay (measured 142 ms per 10k records, `perf/results.json`). Pending owner approval and game-day evidence.
