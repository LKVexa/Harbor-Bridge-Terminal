# INV-18 interface specification (C022–C030)

## 1. Schemas (C022)

Canonical technology: JSON Schema (draft 2020-12 subset) — chosen because the existing
evidence ledger and pk_core records are JSON [S: README]. Source of truth: `wire.SCHEMAS`;
immutable generated artifacts: `schemas/<name>_v<major>.json` (regenerate with
`python tools/gen_schemas.py`; tests/test_wire.py fails if they drift).

| Schema | Purpose | Discriminator / notes |
|---|---|---|
| `PK_FUTURE/1` | typed one-shot handle | `value_type ∈ {str,int,float,bool,bytes,object}`, `epoch` |
| `PK_FUTURE_RESOLVE/1` | value or error resolution | `outcome=ok ⇒ value`, `outcome=error ⇒ error (PK_FUTURE_ERROR/1)`; `idempotency_key` required |
| `PK_FUTURE_ABANDON/1` | writer dropped | `reason ∈ {writer_dropped, writer_crashed, shutdown}` |
| `PK_FUTURE_ERROR/1` | structured failure | stable `code`, `category`, `retryable`, redacted `details`, optional `cause` (depth ≤ 4) |
| `PK_FUTURE_STATUS/1` | component status | see docs/OBSERVABILITY.md |

Identifiers: `^[A-Za-z0-9._:-]{1,128}$` for `future_id`, `correlation_id`,
`idempotency_key`; trace context: W3C `traceparent`. Encoding: UTF-8 JSON, sorted keys,
no insignificant whitespace, NaN/Infinity forbidden (`wire.encode`). Undeclared top-level
fields are rejected; forward-compatible additions go in `ext`, which receivers ignore.

## 2. Authentication (C023) and authorization (C024)

| Boundary | Producer identity | Consumer identity | Control plane | Artifact provider | Mechanism |
|---|---|---|---|---|---|
| in-process `Future` | object holder | object holder | — | — | none (not a trust boundary) |
| in-process `Runtime` | `ResolverCap` | `ReceiverCap` | `AdminCap` | — | 128-bit capability tokens, constant-time compare |
| wire adapter | token `sub` + `cap:resolve` | token `sub` + `cap:receive` | token `cap:administer` | — | HMAC-SHA256 bearer token (`auth.py`); mTLS required by config when exposed |
| pk_core / release artifacts | — | — | — | release pipeline | SHA-256 digests, optional HMAC seal (`tools/gate.py`) |

Credential lifecycle: tokens ≤ `credential_ttl_max_s` (900 s), single use (nonce replay
cache), key rotation with overlap (`KeyRing.rotate`), revocation list. Failures:
`UNAUTHENTICATED`, `PERMISSION_DENIED`, `REPLAY_DETECTED`, `DEPENDENCY_UNAVAILABLE`.
Authentication happens before any state is read or mutated; failures emit
`auth.failure` audit events.

Capabilities: `create, resolve, abandon, receive, inspect, administer`. Resolve rights do
not imply receive rights and vice versa; observers cannot mutate or consume; handles are
scoped to one future and one tenant; they cannot be delegated beyond passing the object
(in-process) and cannot be forged (random tokens); revocation = release on terminal+taken
(the registry entry and all its tokens disappear) or `disable(scope="tenant:X")`.
Least-privilege default: `Runtime.create` returns only resolver + receiver; observer caps
are derived explicitly. Denials are audited (`capability.denied`, `admin.denied`).

## 3. Timeout, cancellation, retry, idempotency, backpressure (C025)

* Resolution has **no** timeout in the primitive; a producer may take as long as it likes.
* Receiving may time out: `Future.wait(timeout)` / `Runtime.take_wait(cap, timeout)`.
  The timeout is owned by the **caller**; expiry returns `False` / raises `TIMEOUT` and
  leaves the future intact (it can still be resolved and taken).
* Cancellation is receiver-initiated and terminal (`CANCELLED`); abandonment is
  writer-side (`ABANDONED`). Resolve racing cancel: whichever takes the lock first wins;
  the loser gets `Cancelled` (producer) or `False` (receiver).
* Retry-unsafe: every local transition. Retry-safe: wire `resolve`/`abandon` **with the
  same `idempotency_key`** — the endpoint returns the cached response for an identical
  body and `REPLAY_DETECTED` for a different body under the same key.
* Backpressure: admission rejects with `RESOURCE_EXHAUSTED` at `max_outstanding` /
  `max_per_tenant`; clients do not auto-retry it (caller decides).

## 4. Errors (C026)

See `errors.py` — codes: `FUTURE_ALREADY_RESOLVED, FUTURE_ALREADY_TAKEN, FUTURE_ABANDONED,
FUTURE_CANCELLED, INVALID_ARGUMENT, TYPE_MISMATCH, UNAUTHENTICATED, PERMISSION_DENIED,
REPLAY_DETECTED, STALE_EPOCH, INCOMPATIBLE_VERSION, INVALID_CONFIG, RESOURCE_EXHAUSTED,
DEPENDENCY_UNAVAILABLE, TIMEOUT, COMPONENT_DISABLED, INTERNAL_INVARIANT, UNKNOWN`.
Messages are human text; codes are the contract; details are redacted and bounded;
`cause` carries a chain. Telemetry records codes, never parses messages.

## 5. Cross-version compatibility (C027)

Supported majors: `{1}`. `wire.negotiate(offer)` picks the highest common major, fails
`INCOMPATIBLE_VERSION` for an unsupported-old or unsupported-new peer, and never
silently downgrades. A document whose `schema` names another major of a known family is
refused with `INCOMPATIBLE_VERSION` (not parsed as v1). Unknown fields: top-level
rejected, `ext` ignored. Unknown error codes → `UNKNOWN` + `original_code`. Fixtures per
supported version live in `fixtures/v1/`. N↔N-1 tests become active when major 2 exists
(`conformance/COMPAT_MATRIX.json` marks them N/A today).

## 6. Resource limits (C028)

docs/ARCHITECTURE.md §5. Enforcement order at the wire adapter: size (before JSON
parsing) → schema → identifiers → admission. Boundary and boundary+1 tests:
tests/test_runtime.py::LimitsTest, tests/test_wire.py::LimitTest.

## 7. Fixtures and reference examples (C029)

`fixtures/v1/*.json` — each fixture has `request` (wire document or bytes), `op`, and the
`expect`ed response code/body. `python tools/conformance.py` executes every fixture
against a fresh endpoint; tests/test_wire.py::FixtureTest runs it in CI. Reference
producer/consumer: `examples/producer_consumer.py` (executed by tests so documentation
cannot drift).

## 8. Adjacent layers (C030, C083)

| Layer | Relation [S] | Double | Paths tested |
|---|---|---|---|
| INV-15 async ABI | upstream: readiness via waitable sets | `adjacent.WaitableSet` | ready, pending, abandoned, version |
| INV-12 interop | upstream: lowers/lifts value | `adjacent.Codec` | round-trip, type mismatch, malformed |
| INV-16 async functions | downstream: return is a completion | `adjacent.async_call` | return, exception, producer crash, timeout, trace |
| INV-17 streaming | peer: many-shot counterpart | `adjacent.completion_from_stream` | one item, zero (abandon), many (error) |
| INV-20 HTTP worlds | downstream: trailers resolve | `adjacent.http_trailers` | 2xx, 5xx, missing trailers, malformed, duplicate |

Real-component tier: tests/test_integration_real.py runs when `INV18_REAL_COMPONENTS`
points at the real packages; otherwise it **skips**, and the release gate treats that
mandatory skip as BLOCKED — the doubles cannot satisfy the real tier.
