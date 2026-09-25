# INV-35 Normative Requirements (v4.3.0)

Requirement IDs `R-xxx` are stable. Each maps to checklist rows and to the tests
that verify it in `requirements/traceability.json` (generated; CI fails on drift).
Keywords SHALL/SHALL NOT/SHOULD/MAY per RFC 2119. Approval: **PENDING** (accountable_owner).

## 1. Functional requirements — source function: separate orchestration and bulk-data channels (C011)

| ID | Requirement | Verified by |
|---|---|---|
| R-001 | The component SHALL expose orchestration operations only through `ControlPlane` and bulk operations only through `Datapath`. | T01, T04 |
| R-002 | A capability SHALL grant actions from exactly the declared set; bulk actions (`submit`,`complete`) SHALL NOT authorise any control action and vice versa. | T01 |
| R-003 | Every descriptor SHALL be validated against the queue's registered guest-memory regions before any queue, quota, idempotency or journal state changes. | fixtures, fuzz, T10 |
| R-004 | Chains that loop, dangle, exceed `chain_limit` descriptors or `byte_limit` bytes SHALL be refused with a stable code. | fixtures, fuzz |
| R-005 | In-flight descriptors per queue SHALL NOT exceed `depth_limit` (≤ `QUEUE_DEPTH`=64). | concurrency |
| R-006 | A completion SHALL notify the guest whenever work remains pending; suppression MAY occur only when drained and requested. | concurrency (lost-wakeup) |
| R-007 | Every refusal SHALL carry a registered `INV35-Exxx` code with an outcome class. | contracts |
| R-008 | Queue ownership SHALL be bound to one tenant; any cross-tenant call SHALL be refused (E305) and audited. | T02 |
| R-009 | Lifecycle changes SHALL follow `schemas/status/lifecycle.json`; illegal transitions SHALL be refused (E400). | LifecycleTest |
| R-010 | A QUARANTINED queue SHALL refuse both admission and completion side effects and SHALL NOT return directly to SERVING. | faults |
| R-011 | Commands carrying a stale controller epoch SHALL be refused (E307). | T17 |
| R-012 | A retried submit carrying the same `(tenant, idempotency_key)` SHALL NOT be applied twice, including across restart. | faults |
| R-013 | Configuration SHALL be fully validated before activation; a failed activation SHALL leave the active configuration unchanged. | ConfigTest |
| R-014 | Security-critical configuration fields SHALL only be tightened by override layers. | T11 |
| R-015 | Secret material SHALL NOT be accepted in configuration and SHALL NOT appear in logs, metrics, decisions or audit. | T11, T14 |
| R-016 | Loss of key or time service SHALL fail closed (E306) and mark the component not-ready. | T09 |
| R-017 | Audit entries SHALL be hash-chained and MACed; any modification, reorder or truncation SHALL be detectable. | T15 |
| R-018 | After a crash, recovery SHALL restore exact reservations and bring previously serving queues up FROZEN. | faults |
| R-019 | Peers SHALL negotiate interface majors; no common major SHALL yield E503. | integration |
| R-020 | Status SHALL report live, ready, version, config digest/generation, dependencies, capabilities, saturation and stalls. | contracts, HealthTest |

## 2. Deployment behaviour profiles (C012)

| Profile | Host descriptor capacity | Tenant share | Queue depth | Offline grace | vhost offload | Telemetry sample | Rationale |
|---|---|---|---|---|---|---|---|
| cloud | 65 536 | 5 % | 64 | 300 s | on | 1.0 | dense multi-tenant; strict fairness |
| datacenter | 16 384 | 10 % | 64 | 300 s | on | 1.0 | default |
| near_edge | 4 096 | 25 % | 64 | 1 800 s | off | 1.0 | intermittent uplink |
| far_edge | 1 024 | 50 % | 32 | 86 400 s | off | 0.1 | constrained CPU/memory/uplink; fewer tenants |

Profiles are data (`runtime/config.py::PROFILES`, rendered in `config/defaults/`). Safety semantics are identical in every profile.

## 3. Non-functional requirements and targets (C013)

| ID | Dimension | Target | Budget | Evidence |
|---|---|---|---|---|
| N-01 | Memory safety | 0 descriptors dereferenced outside guest memory | none | fuzz, fixtures |
| N-02 | Liveness | 0 lost wakeups with work pending | none | concurrency |
| N-03 | Isolation | 0 cross-tenant accepts | none | T02 |
| N-04 | Reference-model latency (CPython, 4-desc cycle) | p50 ≤ 250 µs, p99 ≤ 1 000 µs (facade) | gate | `benchmarks/thresholds.json` |
| N-05 | Refusal cost | overload refusal p99 ≤ 100 µs | gate | bench |
| N-06 | Production throughput | p50 ≥ 90 % of backend line rate | 5 % below | **backend-owned** (WVR-003) |
| N-07 | Availability (control surface) | 99.95 % monthly | 21.9 min | `docs/operations/SLO.md` |
| N-08 | Recovery | journal replay of 32 records ≤ 5 ms (ref.) | gate | bench |
| N-09 | Tenant fairness | per-tenant p50 spread ≤ 2.0× | gate | bench |

## 4. Result semantics (C014)

| Class | Meaning | Caller action | Codes |
|---|---|---|---|
| success | took effect | continue | E000 |
| degraded | took effect under a declared degraded mode | continue; alert on duration | E001 |
| retryable | nothing took effect | retry with same idempotency key under `RetryPolicy` | E200–E203, E306, E401 |
| terminal | nothing took effect | do not retry; fix input or escalate | all others |

## 5. Quota, fairness and capacity (C017, C069)

Per host: `host_descriptor_capacity`. Per tenant: `floor(capacity × tenant_share)`
descriptors in flight and a token bucket (`submit_rate_per_s`, `submit_burst`).
Per queue: `depth_limit`. Per tenant: `max_queues_per_tenant`. Saturation =
in-flight / host capacity, exported as `inv35_saturation`; alert at 0.8 (warn) and 0.95 (page).

## 6. Intermittent/offline network behaviour (C018)

The bulk datapath never needs the control plane for safety. On loss:
within `offline_grace_s` queues run DEGRADED(`control_plane_unreachable`) on
last-good config; beyond it `offline_policy` applies (`serve_last_good` |
`freeze` | `quarantine`). Restoration returns DEGRADED queues to SERVING.
No configuration change is accepted while unreachable (none can arrive).

## 7. Precedence when goals conflict (C019)

1. **Security & isolation** (memory safety, tenant isolation, fail-closed trust) — never traded.
2. **Data residency / tenancy constraints** — a queue never moves tenants or hosts implicitly.
3. **Correctness & liveness** (no lost wakeups, no double apply).
4. **SLO** (latency/availability) — may be sacrificed via degraded modes that keep 1–3.
5. **Cost/efficiency** — last.

Example: if notification suppression is suspected of losing wakeups, enter
`NO_SUPPRESSION` (costs CPU, keeps liveness). If the key service is down, refuse
(costs availability, keeps security).

## 8. Links

`COMPATIBILITY_POLICY.md` (C016/C027) · `INTERFACE_LIMITS.md` (C028) · `INTERFACE_CONTRACT.md` (C025).
