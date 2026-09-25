# Semantics: outcomes, lifecycle, degraded modes, request contract (MC-006, MC-007, MC-015, MC-046)

## Outcome taxonomy (`production/errors.py::Outcome`)

| Outcome | Meaning | Caller action |
|---|---|---|
| `success` | full answer, all constraints honoured | use |
| `partial` | reserved for multi-facet answers where some facets are missing (not emitted in v1) | use with care |
| `degraded` | answer produced under a declared mode (`partitioned_local`, `stale_data`) | use; surface mode |
| `retryable_failure` | no answer; same request may succeed later (`RATE_LIMITED`, `OVERLOADED`, `DEADLINE_EXCEEDED`, `CANCELLED`, `DEPENDENCY_UNAVAILABLE`, `NOT_READY`, `FROZEN`, `INTERNAL`) | retry with backoff, honour `retry_after_ms` |
| `terminal_failure` | retrying the same request cannot help | fix request / escalate |

The complete code list with HTTP mappings is `schemas/error-codes.json` (generated, CI-checked).

## Lifecycle state machines (`production/lifecycle.py`)

* **Node:** discovered → active → draining → retired; active/draining/discovered → quarantined → active|retired.
  (v4.3.0 enforces removal of non-leaf nodes and quarantine; draining is modelled for integrations.)
* **Link:** unknown → up|down|stale; up ↔ suspect → down; down → up (after `up_after_successes`);
  any → flapping (≥ `max_flaps` availability flips in `flap_window_s`, held non-routable) → up when the window clears;
  up|suspect|down → stale after `stale_after_s` without probes.
* **Site:** connected → suspect|partitioned; partitioned → recovering → connected (lease revoked on the way).
* **Coordinator:** follower → candidate → leader → follower (lease expiry, supersession or quarantine).

Illegal transitions raise `IllegalTransition`; histories are bounded and carry reasons.

## Degraded modes (`lifecycle.Mode`, `lifecycle.ALLOWED`)

| Mode | Entered when | Allowed | Reconciliation |
|---|---|---|---|
| normal | default | all | — |
| partitioned_local | origin's site cannot reach the designated cloud | all; answers are `degraded` | on heal: lease revoked, term fences old leader |
| stale_data | selected path uses latency older than `stale_after_s` (policy `degrade`) | all; answers `degraded` | fresh probes clear it |
| frozen | operator `freeze` | reads, status, renew, validate only | operator `unfreeze` |
| not_ready | no active config, or a security dependency is down | none | activate config / restore dependency |

## Timestamps and freshness
`measured_at`/`at` must be ≤ now + 30 s. A link registered without `measured_at` (static, operator-declared
latency) is treated as fresh by design; feeds that measure latency must always send `measured_at`.

## Request contract (MC-015)

* **Timeout:** `deadline_ms` (1–60 000, default 2 000). Checked after admission, before dispatch and before commit.
* **Cancellation:** cooperative via `Deadline.cancel()` for embedded callers; wire callers use deadlines.
* **Retry:** only `retryable_failure`; capped exponential backoff with full jitter, max 4 attempts, 3 s budget
  (`RetryPolicy`), and never beyond the caller's deadline. Mutations must be retried with the **same
  idempotency key** and a **fresh credential** (nonces are single use).
* **Idempotency:** `(tenant, idempotency_key)` → stored response for 600 s; payload fingerprint must match.
* **Backpressure:** per-tenant token bucket (after authz) and global in-flight bound; shed with
  `RATE_LIMITED`/`OVERLOADED` + `retry_after_ms`; the state-store circuit breaker returns `OVERLOADED` while open.
