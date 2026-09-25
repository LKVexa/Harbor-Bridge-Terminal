# INV-31 Operator Notes

## Bootstrap

1. Verify the repository with the standalone test command in `README.md`.
2. Supply the external `pk_core` framework and run the 100-item framework gate.
3. Validate interface schemas and parent-platform dependencies before deployment.

## Safe drain / quarantine

`FunctionPool.destroy_idle()` removes only idle matching instances. It never force-terminates in-flight work. Filtering by tenant and/or version supports targeted drain behavior.

## Capacity refusal

If a cold instance is required while the configured pool ceiling is reached and every pooled instance is busy, the runtime raises `PoolCapacityExceeded`. The caller/parent platform must translate that refusal into its admission-control, retry, or load-shedding policy; this repository intentionally does not invent retry behavior.

## Clock rollback

A negative observed instance age is treated as unsafe. Idle affected instances are destroyed and counted in `clock_rollback_evictions`.

## Rollback

Code/configuration rollout and rollback orchestration are external to INV-31. The repository does not contain a deploy controller, canary controller, or release-state store. See `MISSING_COMPONENTS.md`.

## Process crash / restart semantics

All pool and invocation state in this package is intentionally in-memory and reconstructible. A process restart starts with an empty pool, so the next invocation for each tenant/version is cold. The package performs no internal replay and persists no invocation payload or scratch state. Determining whether an interrupted external invocation may be retried requires an idempotency contract from the caller/transport layer, which is not implemented here.

Because there is no durable INV-31 state, backup/restore of this local pool is not applicable; recovery is reconstruction from an empty pool plus the parent platform's authoritative deployment/tenant/version state.
