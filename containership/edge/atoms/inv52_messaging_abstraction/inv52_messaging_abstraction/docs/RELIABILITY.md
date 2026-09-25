# Reliability — `DOC-INV52-REL` v4.3.0 (C051-C060)

This repository supplies the broker-independent routing contract and a bounded in-memory reference runtime. It does not claim durable delivery; durability, redelivery and durable dead-letter storage belong to INV-53 and the broker (INV-54).

## Failure domains (C051)

| Domain | Failure | INV-52 behaviour | Evidence |
|---|---|---|---|
| Predicate | raises | route skipped, counted, other routes continue; all-fail → dead letter `route evaluation failure` | `test_runtime.py` |
| Subscriber sink | raises / hangs | counted; breaker (`GuardedSink`) opens after N failures → fast dead-letter `PK_MSG_CIRCUIT_OPEN`; a *hanging* sink blocks its publisher thread (no internal timeout — document: sinks must be non-blocking or wrap their own deadline) | `test_resilience_config.py` |
| Process | exit/crash | in-memory policy, subscriptions, dead letters, decisions lost; rebuilt from config at restart (`bootstrap`); undelivered in-memory dead letters are lost — durable DLQ is INV-53 | declared |
| Dapr sidecar | down / 5xx / 429 | retry with jitter (idempotent), then `Outbox` queues, then backpressure | `test_integration.py` |
| Broker | down / partitioned topic | as sidecar; other topics unaffected | `OutboxChaosTest` |
| Node / site | lost | per-site instance; no cross-site state; failover is broker-level (below) | declared |
| Network | intermittent/absent | `Outbox` (order kept, bounded, expiry) | `OutboxChaosTest` |
| Control plane / config store | down | last good generation keeps serving | `ConfigTest` |
| Identity / key / time | down | deny (security dependency) | `test_security.py` |
| Telemetry | down | degrade only | `LifecycleTest` |
| Provider (cloud) | region loss | broker/Dapr responsibility; residency precedence applies | BLOCKED on INV-53/54 design |

## Health and stall thresholds (C052) — PROPOSED

`PubSub.health(stall_after_s=60, backlog_ratio_warn=0.8)`: `degraded` when dead-letter fill ≥ 80 %, any topic frozen/quarantined, or no publish completed in 60 s while traffic is expected; `unhealthy` when lifecycle is not READY/DEGRADED. `ManagedBus.health()` adds dependency probes and readiness (`ready=false` when a security dependency is down).

## Retry (C053)

`RetryPolicy`: ≤ 4 attempts, 50 ms × 2ⁿ capped 2 s, full jitter, idempotent only, deadline-aware. Used by `DaprHttpAdapter`. The in-process publish is never retried internally.

## Admission / load shedding / breaking (C054)

`QuotaAdmission` (per app, optional per topic), `GuardedSink` circuit breakers, `Outbox` capacity. All refuse with retryable codes.

## Failover (C055)

INV-52 holds no replicated state, so failover = re-bootstrapping the instance on another node of the **same site and residency** and pointing the Dapr component at the surviving broker. Rules: never fail over a topic to a broker/site outside `topics[].residency`; tenant namespaces are preserved by config; consistency is at-least-once with id de-duplication. Executed failover evidence: BLOCKED (needs INV-53/54 environment).

## Degraded operation (C056)

Noncritical dependency down → DEGRADED, keep serving; security dependency down → refuse; broken consumer → breaker isolates it.

## Crash consistency, restart, replay (C057)

Configuration: activation is all-or-nothing; restart replays the last approved config. Messages: `Outbox` replay is ordered and idempotent (broker de-duplicates on `id`); in-process dead letters are volatile by design.

## Split brain / stale controllers (C058)

`FencedOwnership` issues monotonic fencing tokens with leases for exclusive consumers/controllers; a stale token is refused (`PK_MSG_STALE_FENCING_TOKEN`). Broker-side consumer-group fencing is INV-54's.

## Quarantine / freeze / disable (C059)

Topic: FROZEN (retryable refusal), QUARANTINED (accepted, held in dead letter, not delivered), DISABLED (terminal refusal). Component: `emergency_disable`. All transitions validated and recorded.

## Fault injection (C060)

`test_integration.py::OutboxChaosTest::test_recovery_objective_under_random_faults`: 500 messages, 30 % injected broker outages, objective **RPO 0, no duplicates, order preserved** — met. Live broker/sidecar fault injection: BLOCKED.
