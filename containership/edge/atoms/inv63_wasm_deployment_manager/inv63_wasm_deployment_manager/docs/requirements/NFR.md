# INV-63 Non-Functional Requirements

| Field | Value |
|---|---|
| Document ID | INV63-REQ-NFR |
| INV-63 C-IDs covered | C013, C014, C018, C061, C062, C063, C064, C070 |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | SRE lead (role), Performance reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when `perf/thresholds.json` / reference hardware changes. |

## 1. Measurement conditions
- Targets: `perf/thresholds.json` — status `PROPOSED - requires owner approval against reference hardware`; `ci_slack_factor: 3.0`.
- Reference hardware: **UNSPECIFIED** (container CI runner). Measured values in `perf/results.json`: Python 3.11.15, x86_64, 2 CPUs, `Linux-6.18.44-fc-v37-x86_64-with-glibc2.39`. Fake lattice (`InMemoryLattice`), deterministic inputs.
- Command: `python perf/bench.py --gate` (exit 1 if any threshold is breached — C070). `gate_failures: []` in the recorded run.
- Approval evidence `perf-approval` is open; numbers must be re-baselined on approved hardware.

## 2. Latency / throughput / resources

| NFR | Metric | Target (thresholds.json) | Measured (results.json) |
|---|---|---|---|
| NFR-01 | `diff_1000_noop_ms` (200 hosts / 10 labels) | p50 5, p95 8, p99 10, max 25 | p50 1.95, p95 2.40, p99 3.11, max 5.63 (n=300) |
| NFR-02 | `diff_1000_cold_ms` | p50 8, p95 12, p99 15, max 40 | p50 2.71, p95 2.82, p99 5.58, max 5.58 (n=100) |
| NFR-03 | `handle_reconcile_noop_ms` (full request path incl. auth, journal fsync) | p50 2, p95 4, p99 6, max 20 | p50 0.446, p95 0.734, p99 1.003, max 3.101 (n=300) |
| NFR-04 | `startup_empty_journal_ms` | max 50 | 2.73 |
| NFR-05 | `replay_10k_records_ms` | max 2000 | 142.1 |
| NFR-06 | `throughput_noop_reconcile_rps` | min 200 | 2008 |
| NFR-07 | `tracemalloc_peak_10k_requests_mb` (Python allocation peak, not OS RSS) | max 64 | 18.6 (current `perf/results.json` still stores it under the old key `rss_growth_10k_requests_mb`; re-run `perf/bench.py`) |
| NFR-08 | contract SLO: p99 diff < 10 ms for 1000 instances (`contract.py`) | = NFR-01 p99 | 3.11 |

Additional measurements (no threshold yet — C063/C064):

| Scenario | Measured |
|---|---|
| Overload: 1000 `Admission.enter` calls, `max_inflight=32`, burst 50 | admitted 32, shed 968 |
| Scale-out 1→200 (set_desired + reconcile) | 53.2 ms |
| Scale-in 200→5 | 48.6 ms |
| Per-tenant: p50 reconcile, 1 vs 50 tenants resident | 0.446 ms vs 0.436 ms |
| Journal bytes per desired (50 tenants, all records incl. lifecycle/idempotency) | 2670 B |

Not measured: soak > 10k requests, fleet-scale (evidence `fleet-scale`), real Wadm latency, edge hardware (see `perf/EDGE_POWER_PLAN.md`), multi-arch.

## 3. Correctness / durability / isolation

| NFR | Requirement | Verified by |
|---|---|---|
| NFR-10 Convergence | second reconcile after convergence emits zero actions | `tests/test_service.py::SemanticsTest::test_desired_reconcile_converges_and_rests`, `tests/test_manager.py::ManagerTest::test_deterministic_spread_and_idempotent_reconcile` |
| NFR-11 Availability in rollout | worst unavailable <= `max_unavailable` (canary batch first) | `tests/test_service.py::RolloutTest::test_canary_then_bounded_batches` |
| NFR-12 Durability | RPO 0 for acknowledged writes (fsync per record) — assumes A-12 | `DurabilityTest` tests |
| NFR-13 Consistency | single fenced writer | `test_stale_controller_is_fenced` |
| NFR-14 Determinism | same inputs → same plan (sorted hosts, heap placement) | `PlacementEquivalenceTest::test_heap_placement_matches_reference` |
| NFR-15 Isolation | no cross-tenant read/write | `AuthZTest::test_cross_tenant_access_blocked` |

## 4. Outcome semantics (C014) — `errors.Outcome`

| Outcome | Meaning | Produced by |
|---|---|---|
| SUCCESS | every requested action committed and the target converged | default in `handle`; `reconcile_ns` no-op / all actions committed |
| PARTIAL | some actions committed; remainder recorded and resumable | `reconcile_ns` when some starts fail |
| DEGRADED | accepted while a non-critical dependency is unavailable; durable locally, resynced later | `reconcile_ns` offline within autonomy window |
| RETRYABLE | nothing committed by this request; retry same idempotency key after `retry_after_s` | errors in `_RETRYABLE`: `OVERLOADED`, `CIRCUIT_OPEN`, `DEADLINE_EXCEEDED`, `DEPENDENCY_UNAVAILABLE`, `CONTROL_PLANE_OFFLINE`, `CONFLICT`, `INSUFFICIENT_CAPACITY` |
| TERMINAL | nothing committed; identical retry cannot succeed | all other `ErrorCode`s |

Caveat: a `DEADLINE_EXCEEDED` in the middle of `reconcile_ns` is RETRYABLE although earlier `action_committed` records exist; retry is safe because reconcile is idempotent. `QUOTA_EXCEEDED` from the per-tenant rate bucket is TERMINAL by catalogue but carries `retry_after_s`.

## 5. Offline behaviour (C018)
Within `offline_autonomy_s` (default 3600; far-edge >= 300, `edge-site-a` 86400): `offline_intent` journaled, lifecycle `DEGRADED`, outcome `DEGRADED`, `status().degraded=true`, gauge `control_plane_up=0`. Window measured on the monotonic clock. Beyond: `INV63-E-CONTROL-PLANE-OFFLINE`, `retry_after_s=reconcile_interval_s`. Rollouts refused offline. Reconnect: `resync()` reconciles pending namespaces; `tick()` calls it automatically when intents are pending. `tests/test_service.py::SemanticsTest::test_offline_mode_queues_intent_then_resyncs`, `::test_offline_beyond_autonomy_window_is_retryable_failure`.
