# INV-52 Scope, Dependencies, Assumptions and Non-goals — `DOC-INV52-SCOPE` v4.3.0

Status: PROPOSED (owner approval pending). Machine-readable form: `governance/dependencies.json`.

## Dependencies (C003)

| Name | Kind | Interface / version | Availability assumption | Failure behaviour in INV-52 | Trust | Upgrade coupling |
|---|---|---|---|---|---|---|
| INV-46 Distributed application runtime | upstream | calls `PubSub.publish/subscribe`; Dapr API v1.0 | per node | `NotServing` / `PK_MSG_BROKER_UNAVAILABLE` retryable | authenticated caller identity comes from here | same Dapr minor line (see COMPATIBILITY.md) |
| INV-49 Pluggable infrastructure adapters | upstream | admits broker adapters against the conformance fixtures | control plane | adapter not admitted → not used | artifact digest + provenance (`security.verify_artifact`) | fixture version |
| INV-53 Message reliability | downstream | redelivery, durable DLQ, dedup store over PK_MSG_ENVELOPE/1 | per site | INV-52 dead-letters locally, bounded | trusts envelope `id` as idempotency key | envelope major |
| INV-54 Broker implementations | downstream | Dapr Pub/Sub components (`pubsub.*`) | per site | `Outbox` queues, then backpressure | broker ACLs + TLS | Dapr component `version: v1` |
| Dapr sidecar (`daprd`) | peer | HTTP `/v1.0/publish/{pubsub}/{topic}`, CloudEvents 1.0 | co-located | retry with jitter, then `Outbox` | `dapr-api-token` from secret store | pinned minor, see COMPATIBILITY.md |
| Identity / key provider (KMS) | peer | `TokenAuthority(keys=...)` callback | per node | every call denied (`PK_MSG_TRUST_UNAVAILABLE`) | root of trust | key rotation window ≥ token TTL |
| Time source (NTP) | peer | `clock()` | per node | invalid clock → deny | ±30 s skew tolerated | — |
| Policy / config store | peer | `ConfigManager.activate` layers | control plane | last good config stays active | author + change_ref recorded | config schema major |
| Telemetry backend | peer (noncritical) | JSON logs, Prometheus text | best effort | component degrades, never blocks | no payloads exported | — |
| DNS | peer | sidecar/broker host names | per node | treated as broker unavailable | — | — |

## Assumptions (C005)

| # | Assumption | Class | Validation |
|---|---|---|---|
| A1 | CPython ≥ 3.10 on any OS/CPU (pure stdlib) | hard requirement | CI matrix; `pyproject.toml` |
| A2 | Wall clock within ±30 s of true time | validated precondition | `TokenAuthority` rejects invalid clocks; skew window 30 s |
| A3 | Monotonic clock available for deadlines/buckets | hard requirement | stdlib `time.monotonic` |
| A4 | Every peer, network path and store can fail independently | design assumption | fault-injection tests |
| A5 | Callers are untrusted until identity is established | hard requirement | `TenantBus` |
| A6 | No filesystem, network, device or subprocess access is needed by the core runtime | hard requirement | module import audit (`test_governance.py::test_core_has_no_ambient_authority`) |
| A7 | Broker supports at-least-once delivery and CloudEvents structured mode via Dapr | validated precondition | conformance fixtures; live Dapr evidence OPEN |
| A8 | Network MTU / connectivity may be intermittent at far edge | degraded-mode assumption | `Outbox` tests |
| A9 | Persistence is provided by the broker, not INV-52 | hard requirement | RELIABILITY.md |
| A10 | Control plane may be unavailable; last activated config keeps serving | degraded-mode assumption | `ConfigManager` keeps generation |
| A11 | Identity/key service unavailability must deny | hard requirement | `test_security.py::test_key_provider_or_clock_outage_denies` |
| A12 | Per-site instance; no global singleton | hard requirement | contract boundaries |

## Non-goals and unsupported deployment patterns (C008)

Non-goals: implementing brokers; guaranteeing delivery or durability; defining application payload schemas; transport encryption (delegated to Dapr mTLS / broker TLS); cross-site total ordering.

Unsupported patterns (a deployment matching any of these is outside the support policy):

1. Using the in-memory `PubSub` as a durable queue or as the only copy of business data.
2. One `PubSub` instance shared by multiple tenants **without** `TenantBus` (tenant isolation relies on it).
3. Wildcard publishers (`"*"`) — rejected by config validation.
4. Taking the publisher identity from the message instead of an authenticated caller.
5. A global singleton bus spanning sites or regions.
6. Secrets in the INV-52 configuration (rejected) or in envelopes, metric labels or dead-letter reasons.
7. Running an adapter not admitted by digest/provenance.
8. Dapr or broker versions outside the compatibility matrix.
9. Predicates with side effects (predicates may run on a read-only view and may be retried).
