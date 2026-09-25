# INV-05 Interfaces and Boundaries

Traceability: C021–C028; MC-012, MC-013, MC-014, MC-020, MC-026, MC-027.

## Boundary inventory (C021)

| Boundary | Protocol / file | Authn (C023) | Authz action (C024) | Deadline default/max (C025) | Limits (C028) |
|---|---|---|---|---|---|
| `POST /v1/txn` | `cstate.txn/1.x` | mTLS SPIFFE (tokens only if enabled) | `read`/`write`/`delete` | 5 s / 30 s | 128 ops/branch, 128 compares, 4 MiB request |
| `POST /v1/range` | `cstate.range/1.x` | mTLS | `read` | 5 s / 30 s | page ≤ 1000, response ≤ 8 MiB |
| `POST /v1/watch` | `cstate.watch/1.x` → NDJSON frames | mTLS | `watch` | stream; idle 300 s | 64 watches/identity, 10 000 total, 10 000 queued events/watch |
| `POST /v1/compact` | `cstate.compact/1.x` | mTLS | `compact` (cluster) | 30 s / 120 s | — |
| `POST /v1/lease/*` | `cstate.lease_*/1.x` | mTLS | `lease` + ownership | 2–5 s | TTL 2–3600 s, 1000 leases/identity |
| `POST /v1/admin/*` | JSON | mTLS (admin purpose) | `admin.*` (cluster) | 10 s / 60 s | — |
| `POST /v1/hello` | `cstate.hello/1.x` | none (no state disclosed) | — | — | 4 MiB |
| `GET /livez /readyz /version` | JSON | none (status only) | — | — | — |
| `GET /metrics` | Prometheus text | mTLS | `admin.diagnostics` | — | ≤ 64 series/metric |
| Replication | `cstate.repl_*/1.0` | mTLS peer purpose | `replicate` | — | ≤ 1000 events/batch (whole revisions) |
| WAL / snapshot files | `CSW1` frames, `cstate.snapfile/1` | file mode 0600, dir 0700, AES-GCM | process identity | fsync per ack | 64 MiB/frame |
| Backup artefacts | `cstate.backup/1` | HMAC-signed manifest, AES-GCM payload | `admin.backup` / `admin.restore` | — | — |
| Audit log | JSONL HMAC chain | file 0600 | append: service; read: `admin.audit_read` | — | — |
| Config overlays | JSON | file ownership | `admin.config` | — | unknown keys rejected |

## Schemas (C022)

Canonical definitions: `schema.py::MESSAGES`, frozen in `conformance/schema_lock.json`; golden vectors: `conformance/golden_messages_v1.json`; behavioural vectors: `conformance/vectors_v1.json`. Unknown-field and duplicate-key rules are in the `schema.py` module docstring. Breaking changes fail CI (`tools/check_compat.py`).

## Timeouts, cancellation, retry, idempotency, backpressure (C025)

* Deadlines: header `x-cstate-deadline-ms` or body `deadline_ms`, clamped to the class maximum (`service.OP_CLASSES`). A request whose deadline passed before execution is rejected with `CSTATE_TIMEOUT` and **does not execute**.
* Cancellation: transport disconnect cancels a watch; `CancelToken` is checked before commit.
* Retry: client `Client.call` — exponential backoff, full jitter, attempt and time budgets, `retry_after_s` floor, only `retryable` codes, mutating txns only with `request_id`.
* Idempotency classes: see `OP_CLASSES[*].retry`; `request_id` makes a txn replay return the original result (`replayed: true`), and reusing the id for a different request is `CSTATE_CONFLICT`. Scope: per authenticated subject.
* Backpressure: token buckets (`CSTATE_QUOTA` + `retry-after`), in-flight gate (`CSTATE_OVERLOADED`), watch fallback to history paging, lag-based `CSTATE_SLOW_CONSUMER`.

## Errors (C026)

`errors.ERROR_CATALOG` — immutable codes, category, retryability, idempotency sensitivity, HTTP mapping; append-only lock `conformance/error_catalog_lock.json`. Only allow-listed detail keys leave the process.

## Version compatibility (C027)

`hello` negotiation selects the highest common `major.minor` and intersects capabilities; different major ⇒ `CSTATE_INCOMPATIBLE_VERSION`. See `docs/COMPATIBILITY.md` for N/N-1 policy.
