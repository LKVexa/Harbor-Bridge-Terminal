# INV-68 interfaces — transport and failure semantics (MC-07; C021–C028)

## Boundaries

| Boundary | Direction | Operation | Capability | Schema |
|---|---|---|---|---|
| SCH-01 → INV-68 | upstream call | `PackingService.pack` | `pack:submit` | `PK_PACK_REQUEST_1` → `PK_PACK_SERVICE_RESPONSE_1` |
| INV-67 → INV-68 | upstream data | Pod requests translated to workloads | `pack:submit` | `PK_PACK_REQUEST_1` |
| INV-68 → GAP-10 | downstream | response consumed for power overlay | — | `PK_PACK_SERVICE_RESPONSE_1` |
| INV-72 ↔ INV-68 | peer | accelerator work split *before* packing | — | — |
| capacity source → INV-68 | dependency | `capacity_source(tenant)` | — | `{cpu, mem, observed_at, source}` |
| operator → INV-68 | control | `freeze` / `unfreeze`, explain, status | `control:freeze`, `pack:explain`, `status:read` | `PK_PACK_STATUS_1` |
| controller → INV-68 | control | `activate_config` / `rollback_config` | `config:activate`, `config:rollback` | `PK_PACK_CONFIG_1` |

The library call is the transport. An HTTP/gRPC adapter, when added, SHALL map
`PackError.status` to its status code, carry `traceparent` in the W3C header, and
forward the bearer token unchanged.

## Timeouts and cancellation (C025)

* Every request has a deadline: caller-supplied `Deadline` or the config
  `request_timeout_ms` (default 2000 ms). The service checks it before admission,
  after capacity lookup, before packing and before responding; expiry →
  `DEADLINE_EXCEEDED` (retryable).
* `Deadline.cancel()` → `CANCELLED` (terminal) at the next check. The pure engine is
  never interrupted mid-computation (bounded by `max_workloads`; 20 000 workloads ≈ 110 ms).

## Idempotency and retries (C025)

* `idempotency_key` (8–128 chars) scoped by tenant. Same key + same request digest →
  the stored response with `replayed: true`; same key + different digest →
  `IDEMPOTENCY_CONFLICT`. Keys live 600 s, at most 4096 per instance (DEBT-002).
* Packing is deterministic and side-effect free except audit, so *every* pack is
  safe to retry; the key avoids duplicate audit records and recomputation.
* Client retry policy (implemented by `adjacent.SchedulerClient`): retry only codes
  whose registry entry says `retryable`; full-jitter exponential backoff, base 50 ms,
  cap 2 s, at most 10 attempts (`resilience.backoff_schedule`).

## Backpressure and limits (C028)

| Limit | Default | Violation |
|---|---|---|
| `max_payload_bytes` | 4 MiB (text requests) | `PAYLOAD_TOO_LARGE` |
| `max_workloads` | 10 000 | `PAYLOAD_TOO_LARGE` |
| `max_name_length` | 253 | `INVALID_REQUEST` |
| `max_concurrency` | 8 in flight | queued |
| `max_queue` | 32 waiting | `OVERLOADED` (retryable, shed immediately) |
| tenant `max_workloads_per_request` | 2 000 | `QUOTA_EXCEEDED` |
| tenant `max_requests_per_minute` | 120 | `QUOTA_EXCEEDED` |
| JSON nesting | parser recursion bound | `INVALID_REQUEST` |
| connections | n/a for the library; adapters SHALL bound them to `max_concurrency + max_queue` | — |

There are no priority classes; shedding is FIFO-by-arrival and per-tenant quotas
provide fairness.

## Structured errors (C026)

`PK_PACK_ERROR/1` (`schemas/PK_PACK_ERROR_1.schema.json`); registry in `ERRORS.json`
(generated from `errors.REGISTRY`): code, outcome class, retryable, status, summary.
Messages and details are redacted; internals are never exposed (`INTERNAL` carries
only a correlation id).

Error-code compatibility: codes are never renamed or reused; new codes may be added
in a minor release (clients MUST treat unknown codes by their `retryable` flag and
`status`); removing a code requires a protocol major.

## Versions (C027)

`request.protocol` lists acceptable versions (string or list). Absent → `PK_PACK/1`
(4.2.0 compatibility). No overlap → `UNSUPPORTED_PROTOCOL` with the supported list in
`details`. Unknown request fields are refused (no silent drops). Responses carry
`protocol` and `component_version`.
