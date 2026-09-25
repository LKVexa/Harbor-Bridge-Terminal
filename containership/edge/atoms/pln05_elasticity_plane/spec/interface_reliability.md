# PLN-05 interface reliability and error contract (1.0.0)

## Interfaces

| Interface | Direction | Mode | Method | Idempotency | Retry by caller |
|---|---|---|---|---|---|
| `observe` PK_DEMAND/1 | GAP-09 → PLN-05 | sync (`submit_demand`) or queued (`enqueue_demand` + `process`) | bytes + credential | idempotent by `message_id`; ordered by per-source `seq` | yes on retryable codes, same `message_id` |
| `limits` PK_CAPACITY_LIMITS/1 | PLN-01 → PLN-05 | sync | bytes + single-use credential | conditionally idempotent: same revision is rejected (`E_OUT_OF_ORDER`), never applied twice | only with a **new** credential; never bump the revision to retry |
| `ceiling.lower` | GAP-10 → PLN-05 | sync | call + single-use credential | idempotent on value (same ceiling = no-op) | new credential |
| `target` PK_CAPACITY_TARGET/1 | PLN-05 → SCH-01/provider sink | sync publish through the `sink` breaker | `decision_id` + `fencing_token` | consumer de-duplicates on `decision_id`; rejects lower fencing tokens | PLN-05 does not retry publication inline; `republish_last` re-emits the persisted decision |
| status / health / explain | operators, probes | sync, in-memory only | — | read-only | yes |
| controls / config | operators | sync, single-use credential | — | not idempotent (each is an audited authority change) | never blindly; read status first |

## Leader routing

Every state-changing call (`observe`, `limits`, `ceiling.lower`, controls, resume) is accepted only by the instance holding the scope's lease; others answer `E_NOT_LEADER` (retryable) and the caller retries against the leader. Tenant-wide controls (`site="*"`, no workload) need a credential valid for every site and lease the tenant's control record.

## Deadlines

The library performs no network I/O; transport adapters SHALL apply: connect 1 s, TLS handshake 2 s, request 2 s, idle 60 s, end-to-end 5 s for `observe`/`limits`; health probes 1 s and SHALL NOT call dependencies (health reads in-memory state only). Internal retries (`reliability.RetryPolicy`) carry a total deadline (`retry.deadline_ms`, default 10 s) and propagate cancellation (`cancelled()` checked before each attempt).

## Retry classes

Retryable: `E_NOT_LEADER`, `E_OVERLOADED`, `E_CIRCUIT_OPEN`, `E_DEADLINE`, `E_STATE_UNAVAILABLE`, `E_SECURITY_DEPENDENCY`, `E_AUDIT_UNAVAILABLE`. All others are terminal for that payload. Defaults: max 4 attempts, decorrelated jitter between 50 ms and 2 s, retry budget 20 % of first attempts (+1 cold start), stop when the input is superseded (`is_stale`). Retries can never amplify stale demand: a retried sample keeps its `observed_at` and is rejected once older than `stale_after_s`; a retried decision cannot apply twice (`message_id`, `decision_id`).

## Limits

payload ≤ 16 KiB; nesting depth ≤ 4; ≤ 32 top-level fields; identifiers ≤ 64 chars `[a-z0-9][a-z0-9._-]*`; queue ≤ `queue_capacity` (1024) with `control_reserve` (32) slots only for control traffic; replay cache ≤ 10 000 nonces (fails closed when full); explain retention `explain.retention`; audit in-memory window 4096, pending buffer 256; metrics ≤ `telemetry.max_series`.

## Overload

Order of protection: early byte-size rejection before queueing → admission (reject `E_OVERLOADED`, or shed lower priority: telemetry < demand < limits < control) → breaker per dependency (`sink`, `coordination`, `audit_sink`) so one failed dependency never disables another path.

## Errors

`PK_ERROR/1` (`schemas/error_v1.json`): `code`, `category`, `retryable`, `severity`, `message` (≤ 200 chars, never payload bytes), `detail` (allow-listed characters only), `correlation_id`. Codes are append-only (`tests/test_units.py::ErrorsTest.test_released_codes_are_stable`).

## Versions

Unknown major version → `E_SCHEMA_VERSION`, listing supported versions. `x-` extensions are ignored (forward compatible); any other unknown field is critical (`E_SCHEMA_UNKNOWN_CRITICAL`). Peers negotiate with `wire.negotiate(family, peer_versions)` → highest common major.

## Ordering

Per-source strict `seq`; no cross-source ordering is assumed. Duplicates and out-of-order samples are rejected without side effects. Queued processing is FIFO within priority class and serialised (a single lock hold covers take + decide).

## Client guidance for siblings

Retry only the retryable codes, with jitter, reusing `message_id`; never mint a new `message_id` for a retry; never retry control/limits with the same credential; treat `E_FENCED` as a signal that another controller owns the scope.
