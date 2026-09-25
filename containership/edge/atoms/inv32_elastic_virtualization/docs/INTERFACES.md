# INV-32 External Interfaces (v4.3.0)

Normative artifacts live in `schemas/` (JSON Schema 2020-12). This document defines semantics the schemas cannot.

## Boundary inventory (C021)

| Boundary | Direction | Artifact | Transport |
|---|---|---|---|
| Adjustment request | in (INV-33, PLN-05, operators) | `resource_adjustment_request.v2.schema.json` | deployment RPC (mTLS) — BLOCKED |
| Adjustment result | out | `resource_adjustment_result.v2.schema.json` | same |
| Error envelope | out | `error.v1.schema.json` (`PK_ERROR/1`) | same |
| Host resources | out | `host_resources.v1.schema.json` | same / metrics |
| Audit event | out/durable | `resource_audit_event.v1.schema.json` | audit segments, export |
| Hypervisor adapter | out | `adapters/base.py` (`PK_HYPERVISOR_ADAPTER/1`) | ADR-0001 |
| Config | in | `config.py::SCHEMA` (`PK_INV32_CONFIG/1`) | files / config service |
| Bootstrap report | out | `PK_INV32_BOOTSTRAP/1` | stdout |
| Health | out | `PK_HEALTH/1` | probe endpoint |
| Metrics | out | Prometheus text (`telemetry.METRIC_DEFS`) | scrape |
| Traces | in/out | W3C `traceparent` | header/field |
| Thermal ceiling (GAP-10) | in | not yet specified — BLOCKED on GAP-10 contract |

## Identifier grammar and limits
`host`, `guest`, `tenant`: `^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$` (≤255). `operation_id`: ≤128, same alphabet.
Control characters are rejected before schema validation. Request size ≤ 4096 bytes, nesting depth ≤ 4, integers
|n| ≤ 2^53−1, no NaN/Infinity, duplicate keys rejected. Batch/fan-out: **1 operation per request** (no batch API).

## Versioning and compatibility (C016, C027)
* Schema IDs carry `family/major`; minor revisions (`urn:…:2.x`) are **additive only** (new optional fields,
  new enum values in *responses*).
* Requests: unknown fields are **rejected** (strict). Responses/events: consumers **must ignore** unknown fields
  and treat unknown enum values as `internal`/opaque.
* Unknown major → `schema_version_unsupported` (terminal). Supported request majors: {2}.
* `PK_RESOURCE_ADJUSTMENT/1` is accepted **only** as a legacy revert record by `model.ElasticHost.revert`.
  Retirement: removed in 5.0.0; sunset date 2027-06-30 (subject to owner approval, see COMPATIBILITY.md).
* Canonical audit hashing: see `conformance/audit_canonical_v1.json`.

## Timestamps and clocks
Audit events carry `wall_time` (POSIX seconds, float, host clock) and `monotonic_ns` (host monotonic). Ordering
is by `sequence`; wall time is informational. Credentials allow ±30 s skew. Trusted time source (NTS/PTP) is a
deployment prerequisite (RUNBOOKS Day-0).

## Deadlines and cancellation
`deadline_ms` (1…600000) is capped by config `operation_timeout_s`. The provider call receives an absolute
monotonic deadline. Cancellation (`controller.cancel(op_id)`): **before mutation** → `cancelled`; **during
provider mutation** → not interruptible, outcome follows provider confirmation or `unknown_outcome`; **after
confirmation** → no effect (use a revert).

## Idempotency
`operation_id` is the idempotency key end-to-end (also sent to the provider). Retention:
`idempotency_retention_s` (default 7 days, min 1 h); only terminal records are pruned. Same ID + same fingerprint
→ original result with `replayed: true`. Same ID + different fingerprint → `replay_conflict`. Same ID while the
outcome is unknown → `unknown_outcome_blocked` until reconciled. A definitively *not applied* operation may be
re-executed under the same ID.

## Retryability (C025)
Every code in `errors.ERROR_CATALOG` carries `retry ∈ {retryable, conditional, terminal}`; `conditional` means
"re-read state (new `expected_version`) before retrying". Overload/quota errors carry `retry_after_s`.

## Backpressure and concurrency (C028)
Per guest: 1 in-flight mutation (others → `guest_busy`). Per host: `max_inflight_per_host` minus
`safety_reserved_slots` for normal/low priority. Per tenant: `max_inflight_per_tenant` and token bucket
(`tenant_rate_per_s`, `tenant_burst`). No unbounded queue: excess is rejected (`overloaded`, `quota_exceeded`).
Low-priority requests are shed first under dependency saturation. Per-controller limit = per-host limit (one
controller owns a host).

## Ordering
Mutations on one guest are serialized; audit `sequence` is a total order per host store. No ordering is
guaranteed across hosts.
