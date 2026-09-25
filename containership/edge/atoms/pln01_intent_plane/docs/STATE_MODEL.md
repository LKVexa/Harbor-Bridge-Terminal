# Non-functional targets, outcome classes, degradation and lifecycle (MC-005)

## Targets
| Property | Target | Measured by |
|---|---|---|
| Plan latency | p99 < 2 s @ 10k nodes (CI: 0.08 s max) | `plan_emission_seconds`, perf gate |
| Mutation latency | p99 < 50 ms in-memory, < 250 ms durable w/ fsync | `pln01_request_seconds{op}` |
| Availability | 99.9 % monthly for read/plan; 99.5 % for mutation | readiness probe, request outcome codes |
| Durability | RPO 0 for acknowledged mutations (single host, fsync on) | crash tests `DurableState` |
| Recovery | RTO < 5 min single-host restart; < 30 min restore from backup | runbook drills |
| Consistency | linearizable single writer; plans read one version atomically | concurrency suite |
| Admission correctness | 0 admitted policy violations | `declaration_admission` + audit |

## Outcome classes (every response is exactly one)
`ok` · `ok_noop` (idempotent) · `rejected_terminal` (validation, cycle, policy, secret, artifact, auth) ·
`rejected_retryable` (version conflict, quota, overload, deadline, circuit, trust unavailable, lease) · `internal`.
Retryability is authoritative in `schemas/error_codes.v1.json`.

## Degradation ladder
| Mode | Trigger | Mutations | Plans | Reads |
|---|---|---|---|---|
| normal | all required deps up | yes | yes | yes |
| degraded-observability | GAP-09 down / sites stale | yes | yes (steps held per site) | yes |
| degraded-policy | GAP-13 down | **no** (fail closed, E0005) | yes | yes |
| identity-down | PLN-07 down | **no** (E0010) | **no** (E0010) | **no** |
| frozen/quarantined | operator | no for scope | yes / held | yes |
| disabled | emergency stop | no | release refused | yes |
| store-failed | integrity error | no (fail-stop) | no | restart required |

## Lifecycle of a declaration
`submitted → validated → authenticated → authorized → admitted | rejected → committed(vN) → planned → released → (executed downstream) → superseded(vM) | retracted | rolled_back(as vK)`.
Illegal: any transition skipping `committed`; release of a plan whose `graph_version` ≠ current (`verify_release`).

## Component lifecycle
`bootstrap → recovering (store replay) → ready → degraded ↔ ready → draining → stopped`; `ready` requires the
readiness probe (`Health.readiness`) to pass.
