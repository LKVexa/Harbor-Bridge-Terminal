# INV-72 Accelerated workload requirement — requirements specification (v4.3.0)

Source function: **Hardware-accelerated AI** (GPU passthrough / local inference). INV-72 owns the
*requirement* a job states and the *decision* whether a discovered device satisfies it. It never
discovers devices, schedules, manages drivers or runs models (see `README.md` → "Explicitly does not own").

Every `SHALL` below has an ID. `ops/RTM_SOURCE.json` maps checklist controls to implementation and tests;
the right-hand column here names the test class that verifies each requirement.

## 1. Functional requirements (C011)

| ID | Requirement | Verified by |
|---|---|---|
| F-01 | INV-72 SHALL select only devices whose class equals the requested class exactly. | `test_fuzz.MatcherFuzzTest`, fixtures 001/004 |
| F-02 | INV-72 SHALL select only devices with `mem_gb` ≥ the requested `mem_gb`, and SHALL state the gap when none qualifies. | fixtures 003, `MatcherFuzzTest` |
| F-03 | INV-72 SHALL return exactly `count` distinct devices or none. | `MatcherFuzzTest` |
| F-04 | When `interconnect` is true, all selected devices SHALL share one `(node, link_group)`. | fixture 009, `MatcherFuzzTest` |
| F-05 | A partition SHALL be selected only when `isolation` is explicitly `shared`; omitted isolation SHALL mean `dedicated`; any other value SHALL be rejected. | `AdversarialTest.test_T1…`, fixture 006/013 |
| F-06 | A partition held by another tenant, or a whole device held by any reservation, SHALL NOT be selected. | `StateStoreTest`, `ConcurrencyTest` |
| F-07 | Every non-match SHALL carry a registered reason code and human text; every match SHALL carry a selection rationale. | `ErrorRegistryTest`, `ExplainTest` |
| F-08 | Selection SHALL be deterministic and independent of inventory order. | fixture 010, `MatcherFuzzTest` |
| F-09 | Reservation SHALL be atomic: either all selected devices are reserved or none. | `ConcurrencyTest` |
| F-10 | A repeated `idempotency_key` from the same tenant SHALL return the original reservation; reuse with a different requirement SHALL be rejected. | `StateStoreTest.test_idempotent…` |
| F-11 | Devices SHALL enter a decision only from a verified PK_ACCEL_INVENTORY/1 snapshot (schema, digest, MAC, monotonic generation). | `DiscoveryTest` |
| F-12 | Operators SHALL be able to quarantine, drain, revoke, emergency-disable and roll back configuration. | `OperatorControlTest`, `ConfigTest` |
| F-13 | Residency constraints (`allowed_nodes`) SHALL restrict candidates before selection. | `PrecedenceTest.test_residency…` |

## 2. Execution-tier applicability (C012)

| Behaviour | cloud | datacenter | near_edge | far_edge |
|---|---|---|---|---|
| authentication required | yes | yes | yes | yes (may be disabled only here, single-tenant) |
| inventory MAC required | yes | yes | yes | yes |
| inventory freshness bound | 300 s | 600 s | 900 s | 3600 s |
| offline grace (degraded answers) | none | none | 1800 s | 86400 s |
| shared partitions | allowed | allowed | allowed | **refused** (forced dedicated) |
| max inventory / count | 4096 / 64 | 4096 / 64 | 512 / 16 | 16 / 4 |
| admission rate / burst / in-flight | 2000/200/256 | 2000/200/256 | 200/50/32 | 20/10/4 |

The table is generated from `config/profiles/*.json`; `ConfigTest.test_every_tier_profile_validates`
proves each profile is valid.

## 3. Non-functional requirements (C013)

| ID | Attribute | Requirement | Status |
|---|---|---|---|
| N-01 | latency | p99 decision < 10 ms at ≤ 4096 devices (contract SLO) | measured; straddles the bound at 4096 (W-005) |
| N-02 | availability | ready whenever config active, inventory fresh/degraded and not disabled; stall detected after 60 s without progress | `HealthTest` |
| N-03 | durability | an acknowledged reservation survives process crash when a journal path is configured (fsync before ack) | `FaultInjectionTest` |
| N-04 | consistency | single-writer per store enforced by fencing; stale leader refused | `FaultInjectionTest.test_controller_failover…` |
| N-05 | determinism | identical inputs → identical selection | fixtures, fuzz |
| N-06 | isolation | zero cross-tenant partition shares; zero sub-requirement placements (no error budget) | fuzz, concurrency |
| N-07 | bounded resources | every input, table and buffer has a documented bound (`matcher.MAX_*`, admission tenant table, nonce cache, audit buffer, decision ring, metric series) | `LimitsTest`, `ResilienceTest`, soak |

## 4. Outcome semantics (C014)

`success` · `refused` (clean explained non-match; do not retry unchanged) · `retryable` (deadline,
cancel, overload, circuit, stale inventory, dependency down; retry with backoff) · `degraded`
(answered from last verified inventory inside offline grace; flagged in `degraded[]`) · `terminal`
(malformed, unauthorised, replay, stale fence, disabled; never retry unchanged). Partial success
does not exist by construction: F-09. The authoritative code→outcome table is `errors.REGISTRY`.

## 5. Lifecycle (C015)

See `lifecycle.py` (`REQUEST`, `DEVICE`). Terminal request states: refused, rejected, cancelled,
expired, released, revoked.

## 6. Versioning and compatibility (C016, C027)

See `ops/COMPATIBILITY_POLICY.md`. SemVer for the component; wire schemas are `NAME/<major>`.

## 7. Capacity, quotas, fairness (C017)

Per-tenant device quota (`quotas.default_devices_per_tenant`, `quotas.per_tenant`), refusal code
`ACCEL_QUOTA_EXCEEDED`. Fairness of *decision* capacity: per-tenant token buckets, so one tenant's
burst sheds only that tenant. Fleet capacity and saturation: `capacity.py`.

## 8. Intermittent or absent network (C018)

Inventory older than the freshness bound is served only inside the profile's `offline_grace_s`,
and every such answer is `degraded`. Beyond it: `ACCEL_INVENTORY_STALE` (fail closed). An
unreachable identity/key service is always `ACCEL_DEPENDENCY_UNAVAILABLE` — there is no offline
grace for authentication.

## 9. Precedence (C019)

security > residency > correctness > SLO > cost (`precedence.py`). Each application of the rule is
written into the decision's rationale.
