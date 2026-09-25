# INV-31 Normative Requirements (C005, C011, C012, C013, C018, C019)

Each SHALL names the test that verifies it. `BLOCKED` means the requirement depends on
an input that was not supplied and has no verifying test in this package.

## R-REUSE — instance reuse (owned, C011)
| ID | Requirement | Verified by |
|---|---|---|
| R-REUSE-1 | INV-31 SHALL reuse an instance only when tenant and code version both match exactly. | `test_component.py::test_tenant_and_version_are_strict_reuse_boundaries`, `FuzzAndPropertyTest` |
| R-REUSE-2 | INV-31 SHALL clear invocation-scoped scratch state before an invocation returns. | `FuzzAndPropertyTest::test_randomised_operation_sequences_preserve_invariants` |
| R-REUSE-3 | INV-31 SHALL NOT reuse an instance whose age is negative or exceeds `max_age`. | `test_age_eviction_and_clock_rollback_are_fail_closed` |
| R-REUSE-4 | INV-31 SHALL report cold/warm and a stable `decision_reason` for every invocation. | `test_cold_then_warm_reuse_and_state_clear` |
| R-REUSE-5 | INV-31 SHALL NOT carry instances across configuration generations. | `ConfigTest::test_no_reuse_across_config_generations` |

## R-BOUND — invocation boundary (owned)
| ID | Requirement | Verified by |
|---|---|---|
| R-BOUND-1 | Every invoke, drain, explain, disable and configuration call SHALL be authenticated by a signed, unexpired, non-replayed assertion. | `AuthenticationTest` |
| R-BOUND-2 | A caller SHALL hold `invoke:<tenant>` and be bound to that tenant to invoke. | `AuthorizationTest` |
| R-BOUND-3 | Unknown request schema versions and unknown fields SHALL be refused, never ignored. | `VersioningTest` |
| R-BOUND-4 | A repeated idempotency key with the same request SHALL return the first result without re-executing; with a different request it SHALL fail with `INV31-E-IDEMPOTENCY-CONFLICT`. | `ControlSemanticsTest` |
| R-BOUND-5 | Every failure SHALL carry a stable code from `PK_INV31_ERROR/1`. | `ErrorsTest`, `FuzzAndPropertyTest::test_hostile_*` |

## R-DAG — HTTP/RPC pure-compute DAG semantics (C011, C031) — BLOCKED
The DAG model (node purity, edge serialisation, partial-failure semantics) is defined by
Dandelion, which was not supplied (A03). INV-31 SHALL NOT inspect or execute DAG
contents; it only binds an instance to (tenant, version). No SHALL about DAG semantics
is written here because it would be invented.

## Deployment contexts (C012)
| Context | Example config | Differences |
|---|---|---|
| cloud / datacenter | `config/cloud.example.json` | defaults |
| near-edge | `config/near-edge.example.json` | smaller pool, shorter max_age |
| far-edge | `config/far-edge.example.json` | concurrency 1, pool 16 |
All four examples are marked `EXAMPLE-UNAPPROVED`; sizing needs measurements on real hardware (C068 BLOCKED).

## Non-functional requirements (C013)
Isolation and version fidelity: zero budget (contract SLOs). Determinism: for a fixed
sequence of (tenant, version, tick) inputs the reuse decision is deterministic
(property test). Latency thresholds: see `SLOS.md` — **PROPOSED, not approved**.
Availability/durability: INV-31 holds no durable state; availability is inherited from PLN-04.

## Network absent or intermittent (C018)
INV-31 opens no sockets (asserted by `test_no_ambient_authority_in_sources`). If the
execution plane is unreachable → fail closed (`INV31-E-DEPENDENCY-UNAVAILABLE`, not ready).
If observability is unreachable → serve, mark degraded, buffer ≤10,000 records, count drops.
If the key/identity source is unreachable → no new keys load; an empty key store refuses all callers.

## Precedence when requirements conflict (C019)
1. Tenant isolation and security (never traded). 2. Residency (not modelled by INV-31;
parent platform). 3. Correctness/version fidelity. 4. Availability SLO. 5. Warm-rate
SLO. 6. Cost. A cold start is always an acceptable way to satisfy 1–3 at the expense of 4–6.

## Assumptions (C005)
Nodes: a single process per pool; pools do not migrate between sites. Runtime: CPython ≥ 3.10.
Network: none required by INV-31. Storage: none; all state is in memory and lost on restart,
which is safe because restart = cold. Control plane: supplies keys, configuration documents
and a monotonic logical tick; tick rollback is treated as unsafe.
