# ADR-001 — Completion primitive `future<T>`

| Field | Value |
|---|---|
| Status | **PROPOSED** (approval by the approving authority is pending; the release gate refuses GO until this reads `ACCEPTED`) |
| Deciders | approving_authority (governance/OWNERS.json) |
| Proposed | 2026-09-23 (v4.3.0) |
| Approved | — |
| Next review | 2027-03-23 |
| Supersedes / superseded by | none / a later ADR-NNN sets `Superseded-by: ADR-NNN` here and flips status to `SUPERSEDED` |

## Problem

The post-Kubernetes component model needs a way to hand **exactly one** deferred
result — a value or an error — from one producer to one receiver, and to tell the
receiver when the producer disappeared without answering (source fact: contract.py
`responsibility`, `mandatory`).

## Decision

A separate one-shot type, `Future[T]`, with this state machine:

```
PENDING ─resolve────────▶ VALUE      ─take▶ consumed
PENDING ─resolve_error──▶ ERROR      ─take▶ consumed
PENDING ─abandon────────▶ ABANDONED  ─take▶ consumed (raises Abandoned)
PENDING ─cancel─────────▶ CANCELLED  (receiver consumed by the cancel)
```

* at most one terminal transition; terminal states never revert; no overwrite;
* exactly one receiver consumes; a second receives `AlreadyTaken`;
* an error resolution is an ordinary tagged outcome `("error", msg)`, not an exception;
* abandonment raises on the receiver, so a dropped writer is never a silent hang;
  in the governed `Runtime` dropping the last `ResolverCap` abandons automatically.

**Why separate from a stream (INV-17):** a stream-of-one keeps the receiver's loop and
the writer's ability to send twice; the type-level one-shot removes both (source fact:
README rationale). The INV-17 adapter converts a stream to a completion only if it
carries exactly one item.

**Thread-safety:** one `threading.Condition` (wrapping a `Lock`) per future serialises
every transition. The lock release/acquire pair is the happens-before edge between the
resolving and the receiving thread. `wait(timeout)` blocks on the condition.

**Process-local only.** Cross-process/distributed futures are *not* this primitive.
The wire adapter (`adapters.py`) exposes a local future remotely with a single
authoritative owner, epoch fencing and idempotency keys; it does not make the future
durable or replicated.

**Memory ownership:** the future holds a reference to the value until `take`, then drops
it; the governed runtime deletes the registry entry once terminal *and* consumed. The
payload is never copied (measured: identity preserved, `bench.profile_ops`).

**Errors:** exception-based Python API (`AlreadyResolved`, `AlreadyTaken`, `Abandoned`,
`Cancelled`, `Rejected`) where every exception carries a stable `code`; `errors.py` maps
any exception to a `PK_FUTURE_ERROR/1` record at every boundary.

## Rejected alternatives

| Alternative | Why rejected |
|---|---|
| `queue.Queue(maxsize=1)` | permits a second `put` after a `get`; no abandonment; no error tagging |
| promise/future pair (`concurrent.futures.Future`) | allows `set_result` only once but lets many callers read `result()` (broadcast) — violates single receiver; no abandonment on writer drop |
| `threading.Event` + shared variable | check-then-write races unless an extra lock is added; reinvents this primitive without the invariants |
| stream-of-one (INV-17) | see above — keeps loop and double-send hazards |
| callback-only primitive | receiver cannot pull; abandonment and exactly-once delivery become caller conventions |

## Trade-offs

* Blocking vs polling: both offered (`wait` / `take` returning `None`); polling is deprecated (DEP-1).
* async integration: not asyncio-native; an asyncio adapter would wrap `wait` in `run_in_executor` (future work, not claimed).
* Fairness: `Lock` gives no FIFO guarantee; exactly one winner is guaranteed, *which* one is not.
* Cancellation: a receiver-side terminal state distinct from abandonment.
* Transport independence: the core does no I/O; transport lives only in adapters.
* Memory: ~1.2 KB per bare future, ~3.0 KB per governed future (measured, reference container).

## Compatibility

`pk_core` integration is unchanged (`component.py`, `contract.py`) and loaded lazily.
Adjacent contracts INV-12/15/16/17/20 are exercised through contract doubles in
`adjacent.py`; real-component tests are a separate tier.

## Consequences

* **Security:** capabilities split resolve/receive/inspect/administer; tokens are 128-bit, compared in constant time.
* **Performance:** the bare primitive is ~1 µs p50 per transition in CPython; the governed runtime ~30 µs per cycle; lock convoy above 2 threads (DEBT-PERF-01).
* **Operations:** state is not durable; a process restart loses pending futures and fences old peers by boot epoch.
