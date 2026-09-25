# INV-52 interfaces — `DOC-INV52-IF` v4.3.0 (C021-C028)

## Boundary inventory (C021)

| # | Boundary | Kind | Contract | AuthN (C023) | AuthZ / capability (C024) |
|---|---|---|---|---|---|
| B1 | `PubSub.publish(app, topic, msg)` | in-process API | PK_MSG_PUBLISH/1 | none — caller MUST pass an already-authenticated `app` | topic allow-list; `source == app` |
| B2 | `PubSub.subscribe / unsubscribe` | in-process API | PK_MSG_SUBSCRIBE/1 | none (application-owned) | route limit |
| B3 | `TenantBus.publish / subscribe / dead_letters` | in-process API for multi-tenant hosts | PK_MSG_PUBLISH/1 + signed token | HMAC-SHA256 token, expiry ≤ 3600 s, single-use nonce, key from provider | `publish:<topic>` / `subscribe:<topic>` per (tenant, app); tenant-namespaced topics |
| B4 | `schemas.parse_publish_request(bytes)` | untrusted wire bytes (HTTP body / frame) | PK_MSG_PUBLISH/1 JSON | by the hosting server before B1/B3 | as B1/B3 |
| B5 | `DaprHttpAdapter.publish` → `daprd` | outbound HTTP | Dapr v1.0 publish, CloudEvents 1.0 | `dapr-api-token` header from secret provider; mTLS by Dapr Sentry | Dapr component `scopes` |
| B6 | Dapr delivery → `dapr_delivery_status` | inbound HTTP (hosting app) | CloudEvents 1.0 → SUCCESS/RETRY/DROP | Dapr app-api-token / mTLS | as B1 |
| B7 | `ConfigManager.activate / rollback` | control-plane API | PK_MSG_CONFIG/1 | operator identity recorded as `author` (authentication by the platform change system) | change record (`change_ref`) |
| B8 | `PubSub.set_topic_state`, `ManagedBus.emergency_disable` | operator control | topic / component lifecycle | platform operator authentication | RACI `emergency_disable` |
| B9 | `metrics()`, `health()`, `explain()`, `decisions()`, `prometheus_text` | observability read API | PK_MSG_HEALTH/1, PK_MSG_DECISION/1 | platform | explain/decisions contain message ids → restricted to operators |
| B10 | `observer` callback, `StructuredLogger.sink` | telemetry export | JSON lines | — | payload never exported |
| B11 | `pk_core` component (`component.py`, `contract.py`) | audit framework | pk_core Contract | — | — |

No WIT, device or hypervisor boundary exists in this component (declared, not omitted).

## Schemas (C022)

`schemas/PK_MSG_{ENVELOPE,PUBLISH,SUBSCRIBE,CONFIG,DECISION,HEALTH}_1.schema.json`. The test suite checks runtime outputs against them with the stdlib subset checker in `schemas.py`.

## Timeouts, cancellation, retry, idempotency, backpressure (C025)

* **Timeout/cancel:** `resilience.CallContext.with_timeout(s)` (0 < s ≤ 3600) carried into adapter publish; cancellation is cooperative (`PK_MSG_CANCELLED`, terminal), deadline expiry `PK_MSG_DEADLINE_EXCEEDED` (retryable). Default Dapr HTTP timeout 5 s.
* **Retry:** only idempotent operations and only `retryable=true` errors; `RetryPolicy` default 4 attempts, exponential ×2 from 50 ms capped at 2 s, full jitter; never sleeps past the deadline.
* **Idempotency:** the envelope `id` is the idempotency key. `PubSub(dedup_window=N)` and broker-side de-duplication (`InMemoryBroker`, INV-53) make replay safe. Default config enables a 4,096-id window.
* **Backpressure:** `QuotaAdmission` token buckets and `Outbox` capacity return retryable `PK_MSG_OVERLOADED`; nothing grows without bound.

## Failure codes

| Code | Retryable | Meaning |
|---|---|---|
| PK_MSG_TOPIC_DENIED | no | topic permission, capability or source-spoofing refusal |
| PK_MSG_ENVELOPE_INVALID | no | malformed envelope, request or CloudEvent |
| PK_MSG_ARGUMENT_INVALID | no | bad argument / limit |
| PK_MSG_SUBSCRIPTION_INVALID | no | bad subscription |
| PK_MSG_RESOURCE_LIMIT | no | size, depth, route or topic limit |
| PK_MSG_TOPIC_UNAVAILABLE | yes | topic frozen |
| PK_MSG_TOPIC_DISABLED | no | topic disabled |
| PK_MSG_OVERLOADED | yes | admission/outbox backpressure |
| PK_MSG_STATE_TRANSITION_INVALID | no | illegal lifecycle transition |
| PK_MSG_UNAUTHENTICATED | no | token missing/forged/expired/replayed |
| PK_MSG_TRUST_UNAVAILABLE | yes | key, clock or identity dependency down (deny) |
| PK_MSG_BROKER_UNAVAILABLE | yes | sidecar/broker unreachable or 408/429/5xx |
| PK_MSG_BROKER_REJECTED | no | Dapr 4xx (e.g. 403 scope, 404 pubsub) |
| PK_MSG_DEADLINE_EXCEEDED | yes | deadline |
| PK_MSG_CANCELLED | no | caller cancelled |
| PK_MSG_CIRCUIT_OPEN | yes | consumer breaker open |
| PK_MSG_STALE_FENCING_TOKEN | no | stale owner |
| PK_MSG_NOT_SERVING | yes | lifecycle not READY/DEGRADED |
| PK_MSG_CONFIG_INVALID / PK_MSG_CONFIG_NO_PREVIOUS | no | config rejected / nothing to roll back |
| PK_MSG_VERSION_UNSUPPORTED | no | no common contract major |
| PK_MSG_ARTIFACT_REJECTED | no | adapter artifact digest not approved or lacks provenance |

## Limits (C028, C067)

| Limit | Default | Config range | Enforced in |
|---|---|---|---|
| payload (canonical JSON bytes) | 1 MiB | 256 B – 16 MiB | `PubSub.publish` |
| JSON nesting depth | 32 | 2 – 256 | `PubSub.publish`, `parse_publish_request` |
| routes per topic (fan-out) | 256 | 1 – 4096 | `subscribe` |
| topics per bus | 10,000 | 1 – 1e6 | `allow`, `subscribe`, `set_topic_state` |
| dead letters retained | 10,000 | 1 – 1e6 | eviction counted |
| decision records retained | 10,000 | 1 – 1e6 | ring buffer |
| dedup window | 0 (runtime) / 4,096 (config default) | 0 – 1e7 | LRU |
| per-app publish rate / burst | 1000/s / 2000 (config default) | (0,1e7] / ≥1 | `QuotaAdmission` |
| admission key table | 10,000 | ctor | `QuotaAdmission` |
| outbox messages | 10,000 | ctor | `Outbox` |
| token TTL / replay cache | ≤ 3600 s / 100,000 nonces | ctor | `TokenAuthority` (full cache denies) |
| audit chain events | 100,000 | ctor | `AuditChain` (base hash kept) |
| log retention | 10,000 events | telemetry config | `StructuredLogger` |
| string fields (id/source/type/topic/app) | 512 chars | fixed | validation |
| Dapr response read | 64 KiB | fixed | `urllib_transport` |

Concurrency: the runtime is thread-safe; route evaluation runs on the publisher's thread (no internal thread pool, so concurrency equals caller concurrency). Connection limits belong to `daprd`/broker (declared external).
