# INV-31 Interfaces

## `PK_INVOCATION/1`

Produced by `FunctionPool.invoke(tenant=..., version=..., now=...)`.

Required fields include the selected instance, tenant, version, cold/warm flag, decision reason, invocation count on the instance, scratch-clear confirmation, and any instances evicted while making the decision. The authoritative schema is `schemas/PK_INVOCATION_1.schema.json`.

The current Python model raises typed exceptions for invalid input or resource refusal. A transport-neutral structured error schema and stable cross-process error-code registry are not yet implemented; see `MISSING_COMPONENTS.md`.

## `PK_FUNCTION_POOL/1`

Produced by `FunctionPool.pool_snapshot(now)`.

The view exposes validated runtime limits, counters, and instance metadata. Invocation scratch contents are intentionally excluded. The authoritative schema is `schemas/PK_FUNCTION_POOL_1.schema.json`.

## Compatibility

Both interface identifiers are versioned at `/1`. The repository does not yet contain a peer-version negotiation or compatibility matrix. Consumers must therefore treat unknown schema versions as incompatible until the parent platform defines that policy.

## Invocation outcome semantics

- **Success:** `invoke()` returns a `PK_INVOCATION/1` object after the invocation scope has been cleared.
- **Cold start:** a normal successful outcome, not an error or degraded state.
- **Capacity refusal:** `PoolCapacityExceeded`; retry policy belongs to the caller because this layer cannot know whether the operation is idempotent.
- **Per-instance admission refusal:** `ConcurrencyExceeded`; the pool may choose another/new instance, while direct instance callers receive the refusal.
- **Invalid request/configuration:** `TypeError` or `ValueError`; treated as terminal until the caller corrects input.
- **Destroyed instance:** `InstanceDestroyed`; terminal for that instance identity.
- **Internal invariant violation:** `RuntimeError`; fail closed and remove the affected instance from service through the parent operational path.

Timeout, cancellation, transport retry, idempotency keys, and cross-process backpressure remain parent-interface gaps.
