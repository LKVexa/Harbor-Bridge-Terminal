# INV-52 Normative Requirements — `DOC-INV52-REQ` v4.3.0

Status: **PROPOSED** — normative text written by the build; it becomes binding only when the accountable owner in `governance/owners.json` approves it (see `governance/reviews.md`). Every requirement below is traced in `governance/requirements.json` / `governance/RTM.md`.

Keywords SHALL / SHALL NOT / SHOULD follow RFC 2119. "The component" means INV-52 (the contract plus the reference runtime in this package). Adapters are INV-54; reliability is INV-53; the application runtime is INV-46.

## 1. Function: message routing and delivery (C011)

| ID | Requirement | Verified by |
|---|---|---|
| R-ENV-01 | Every published message SHALL carry `id`, `source`, `type`, `time`, `data`; an envelope missing any SHALL be refused with `PK_MSG_ENVELOPE_INVALID` before routing. | `test_runtime.py`, conformance CF-07/08/12 |
| R-ENV-02 | `source` SHALL equal the authenticated publisher identity; otherwise `PK_MSG_TOPIC_DENIED`. | CF-06, `test_security.py::test_source_must_match_token_identity` |
| R-ENV-03 | An optional `traceparent` SHALL be a valid W3C trace-context value and SHALL be propagated unchanged to every subscriber and decision record. | `test_runtime_ext.py::TraceTest` |
| R-PUB-01 | A topic SHALL have no publishers until explicitly allowed (fail closed). | CF-05 |
| R-PUB-02 | Payloads larger than `max_payload_bytes` (canonical JSON) or deeper than `max_json_depth` SHALL be refused as terminal `PK_MSG_RESOURCE_LIMIT`. | CF-09, `test_runtime_ext.py::LimitsTest` |
| R-RTE-01 | Each subscription SHALL be evaluated by its own predicate; a predicate or sink failure SHALL NOT prevent evaluation of other routes. | `test_runtime.py::test_routing_dead_letter_and_predicate_isolation` |
| R-RTE-02 | Subscribers SHALL receive isolated copies; no subscriber or predicate SHALL be able to alter another subscriber's view or the published envelope. | `test_runtime.py::test_subscribers_receive_isolated_copies`, `test_adversarial.py::test_predicate_cannot_escalate_by_mutating_policy_through_message` |
| R-DLQ-01 | A message delivered to zero routes SHALL be retained as a dead letter with a machine-readable reason (`no route matched`, `route evaluation failure`, `handler failure`, `quarantined`). No message SHALL be dropped silently. | CF-03, `test_runtime.py::test_dead_letter_reasons_for_no_route_and_handler_failure` |
| R-DLQ-02 | Dead-letter retention SHALL be bounded; eviction SHALL be counted (`dead_letter_evictions`). | `test_runtime.py::test_dead_letter_is_bounded` |
| R-DEC-01 | Every publish attempt, accepted or refused, SHALL produce a decision record (PK_MSG_DECISION/1) with the outcome and a reason for every route. | `test_runtime_ext.py::DecisionAndExplainTest` |
| R-IDM-01 | With `dedup_window > 0` a second publish of an already-accepted `id` inside the window SHALL NOT be delivered again (outcome `duplicate_suppressed`). | `test_runtime_ext.py::IdempotencyTest` |

## 2. Functional requirements by execution tier (C012)

| Tier | Requirement |
|---|---|
| Cloud | R-TIER-C1: the component SHALL be usable behind the Dapr Pub/Sub HTTP API (`DaprHttpAdapter`) with a cloud broker selected by the Dapr component, without code change. |
| Datacenter | R-TIER-D1: the same artifact SHALL run with a self-hosted broker; only the Dapr component YAML and the INV-52 config overlay change (`examples/config/env.prod.json`). |
| Near-edge | R-TIER-N1: a site SHALL run its own instance (no global singleton); site overlays SHALL lower payload/route/dead-letter bounds (`examples/config/site.edge-1.json`). |
| Far-edge | R-TIER-F1: when the broker or uplink is absent the publisher SHALL use the bounded `Outbox`; messages SHALL be queued in order up to capacity, refused with retryable `PK_MSG_OVERLOADED` beyond it, and replayed in order on reconnect (C018). Age-based expiry SHALL be explicit (`max_age_s`) and counted. |

## 3. Non-functional requirements (C013)

| ID | Class | Requirement (measurable) | Status of target |
|---|---|---|---|
| N-LAT-01 | Latency | reference `publish` with one route: p50 ≤ 250 µs, p95 ≤ 500 µs, p99 ≤ 1 ms, worst ≤ 20 ms on the reference host class | PROPOSED (`perf/baseline.json`) |
| N-OVH-01 | Overhead | p99(publish) − p99(direct deliver) ≤ 1 ms (contract SLO) | PROPOSED |
| N-AVL-01 | Availability | component availability is bounded by the broker/Dapr sidecar; INV-52 SHALL itself add no single point of failure (per-site instance) | design |
| N-DUR-01 | Durability | the reference runtime is in-memory: durability SHALL be provided by INV-53 / the broker; INV-52 SHALL NOT claim durability | boundary |
| N-CON-01 | Consistency | per-publisher order SHALL be preserved by `Outbox`; no cross-publisher total order is promised | tested |
| N-ISO-01 | Isolation | cross-tenant publish/subscribe/dead-letter access SHALL be impossible through `TenantBus` | tested |
| N-DET-01 | Determinism | route evaluation order SHALL be subscription order; outcomes SHALL be a pure function of message, policy and route results | tested |
| N-RES-01 | Resources | every queue, window, table and log SHALL have a finite configured bound (see INTERFACES.md §Limits) | tested |

## 4. Outcome semantics (C014)

| Outcome | Meaning | Caller action |
|---|---|---|
| `success` | ≥1 route delivered, no route failed | none |
| `partial_success` | ≥1 route delivered, ≥1 route failed (recorded per route) | none; operator investigates route errors |
| `dead_lettered` | 0 routes delivered; message retained with reason | none; dead-letter consumer handles it |
| `duplicate_suppressed` | id already accepted within window | none (idempotent success) |
| `quarantined` | topic quarantined; held in dead letter | none; operator releases or discards |
| `retryable_failure` | refused, `retryable=true` (`PK_MSG_TOPIC_UNAVAILABLE`, `PK_MSG_OVERLOADED`, `PK_MSG_BROKER_UNAVAILABLE`, `PK_MSG_DEADLINE_EXCEEDED`, `PK_MSG_TRUST_UNAVAILABLE`, `PK_MSG_NOT_SERVING`) | back off with jitter; retry with the same `id` |
| `terminal_failure` | refused, `retryable=false` (denied, invalid, oversize, disabled, unauthenticated) | do not retry unchanged |
| degraded operation | component state `DEGRADED` (noncritical dependency down): publishes continue; health reports `degraded` | alert per OBSERVABILITY.md |

## 5. Lifecycle (C015)

Component: `CREATED → CONFIGURED → READY ⇄ DEGRADED → DRAINING → STOPPED`, any non-terminal state → `DISABLED` (emergency) → `CONFIGURED`. Topic: `ACTIVE ⇄ FROZEN ⇄ QUARANTINED`, any → `DISABLED` → `ACTIVE`. Only the transitions in `lifecycle.TRANSITIONS` / `runtime.TOPIC_TRANSITIONS` are legal; every other one raises `PK_MSG_STATE_TRANSITION_INVALID` (exhaustively tested).

## 6. Capacity, quotas, fairness (C017)

Per-app token bucket (`per_app_rate`, `per_app_burst`) and optional per-topic bucket; each publisher has its own bucket so a noisy publisher exhausts only its own allowance; the admission key table is bounded (`max_keys`); refusal is retryable `PK_MSG_OVERLOADED`. Ceilings: `LIMIT_RANGES` in `config.py`.

## 7. Precedence when requirements conflict (C019)

1. **Security and integrity** (authentication, authorization, tenant isolation, envelope integrity) — never traded; ambiguity fails closed.
2. **Data residency** (`topics[].residency`) — a message SHALL NOT be forwarded to a broker or site outside its residency even to meet an SLO; failover that would cross residency is refused.
3. **No silent loss** (dead-letter guarantee) — preferred over latency: a message is dead-lettered or refused, never dropped.
4. **SLO** (latency/availability) — shed load (`PK_MSG_OVERLOADED`) before breaching bounds.
5. **Cost** — optimisations (sampling, batching) SHALL NOT weaken 1–4; telemetry sampling never drops failures or security events.

## 8. Open decisions (block completion)

* Owner approval of this document and of every PROPOSED threshold (`perf/baseline.json`, `observability.THRESHOLDS`, `TELEMETRY_POLICY`).
* ADR-0001 approval, including the Dapr/broker pin.
* Residency enforcement across sites needs the INV-53/INV-54 failover design; only the precedence rule is defined here.
