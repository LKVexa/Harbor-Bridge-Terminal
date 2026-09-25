# INV-72 operations reference

## Failure-domain enumeration (C051)

| Domain | Failure | INV-72 behaviour | Evidence |
|---|---|---|---|
| component | exception in a decision | request fails with a registered code; no partial reservation | `ConcurrencyTest`, F-09 |
| process | crash mid-write | journal replay; torn tail truncated | `FaultInjectionTest.test_torn_journal_tail_recovers` |
| VM / node | instance lost | another instance takes leadership with a higher fence | `FaultInjectionTest.test_controller_failover_fences_old_leader` |
| site | site isolated from discovery | offline grace (edge) then fail closed | `DiscoveryTest.test_offline_grace_then_stale` |
| network | partition from GAP-02 / reconnect | degraded, then fresh after reconnect | `FaultInjectionTest.test_discovery_partition_then_reconnect` |
| provider | identity/key service down | `ACCEL_DEPENDENCY_UNAVAILABLE` | `TrustTest.test_key_service_down_fails_closed` |
| dependency | one discovery source bad/spoofed | failover to next *verified* source | `DiscoveryTest.test_failover_to_verified_secondary_only` |
| dependency | telemetry sink broken | counted; decision unaffected | `FaultInjectionTest.test_telemetry_sink_failure_does_not_fail_decisions` |
| control plane | stale controller writes | `ACCEL_STALE_FENCE` | `StateStoreTest.test_stale_fence_refused` |
| storage | journal corrupted mid-file | refused `ACCEL_STATE_CORRUPT`; restore from snapshot | `FaultInjectionTest.test_mid_journal_corruption_refused` |

## Health and stall thresholds (C052)

`ready=false` when: disabled, no active config, inventory `empty`/`stale`, or stalled. `stalled` when
requests are in flight and no request has completed for `stall_after_s` (default 60 s). Inventory
`fresh` ≤ `inventory_max_age_s`; `degraded` ≤ + `offline_grace_s`; else `stale`.

## Failover (C055)

Discovery failover only to sources whose snapshot verifies with *their own* registered key — failover
never widens trust. Controller failover by fencing. Residency constraints (`allowed_nodes`) are applied
before any failover choice, so failover cannot move a workload out of its allowed nodes.

## Degraded operation (C056)

Non-critical: telemetry export, metric series beyond the bound, log sink. Losing them never blocks a
decision. Critical (fail closed): identity/key service, inventory beyond grace, configuration.

## SLOs, error budgets, support (C091)

| SLO | Target | Budget | Measured |
|---|---|---|---|
| strict fit | 0 placements below requirement | none | fuzz invariant, 0 violations |
| isolation | 0 disallowed partition shares | none | fuzz + concurrency, 0 violations |
| decision latency | p99 < 10 ms | 1 % | see `evidence/PERF_RESULTS.json`; at 4096 devices p99 straddles 10 ms |
| availability | ready ≥ 99.9 % monthly | 43 min | not measurable without a deployment |

Support commitments (response per severity) are in `ops/ESCALATION.json`; they bind only once owners
are named (W-001).

## Immutable artifacts vs mutable configuration and state (C032)

| Class | Items | Changes by |
|---|---|---|
| immutable artifact | all `*.py`, `schemas/`, `tests/`, `_vendor/pk_core` — pinned by `SHA256SUMS.txt` | a new release |
| mutable configuration | `config/profiles` (shipped defaults), site/env overlays (outside the archive) | `ConfigStore.activate` (generations) |
| mutable state | reservations, quarantine/drain, fence, nonce cache, decision ring, audit buffer | runtime; durable part = journal + snapshots |

## Efficiency analysis (C065, C066)

See `evidence/OPTIMIZATION_REPORT.json`. Profiling showed device validation ran three times per
governed request (intake, overlay copy, decide). The overlay copy no longer re-validates; intake and
the in-`decide` check remain on purpose (the second defends against post-intake mutation, threat T8).
No network hops, serialization or copies exist on the decision path beyond one Device copy per device.

## Power and thermal (C068)

INV-72 performs no accelerator work; its cost is CPU time per decision (see perf results: ~0.8 ms
per governed request at 256 devices on the measuring host). Power/thermal impact of that CPU time on a
constrained edge node has **not** been measured — no edge hardware was available (W-006).
