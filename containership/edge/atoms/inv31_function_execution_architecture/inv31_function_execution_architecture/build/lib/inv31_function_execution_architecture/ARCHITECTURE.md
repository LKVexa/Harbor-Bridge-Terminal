# INV-31 Architecture Notes

## Lifecycle model

An `Instance` has an immutable identity tuple `(name, tenant, version, created_at)` and mutable operational state consisting of active invocation scopes, invocation count, last-used tick, and destroyed state.

Legal lifecycle:

1. **created / idle** — no in-flight invocation scopes;
2. **active** — one or more scopes exist, never exceeding `concurrency_limit`;
3. **idle** — all scopes completed and cleared;
4. **destroyed** — terminal state; no new work may enter.

`destroy()` refuses to terminate active work. `destroy_idle()` therefore acts as a drain/quarantine primitive rather than a force-kill mechanism.

## Reuse rule

Warm reuse requires all of the following:

- instance is not destroyed;
- requested tenant exactly matches instance tenant;
- requested code version exactly matches instance version;
- caller-supplied time is not earlier than creation time;
- age does not exceed the configured maximum;
- current in-flight count is below the configured concurrency limit.

Any tenant or version mismatch forces a cold instance. A negative age is treated as a clock rollback and is never eligible for reuse.

## Concurrency and scratch isolation

Each successful `enter()` allocates an opaque invocation scope. Scratch data is nested by scope. `leave(scope_id)` removes only that scope. This prevents one concurrent invocation from clearing another invocation's data.

Pool mutation and instance mutation are lock-protected. Pool code always takes the pool lock before reading/mutating pooled instance state, while standalone instance methods take only the instance lock.

## Bounded resource behavior

The pool enforces a hard `max_instances` safety ceiling. If a new cold instance is needed at the ceiling, the least-recently-used idle instance is destroyed first. If every instance is active, creation is refused with `PoolCapacityExceeded` rather than permitting unbounded growth.

This safety ceiling does not replace fleet capacity planning, autoscaling, or fairness policy; those remain parent-platform concerns.

## Clock behavior

Time is represented as a caller-supplied non-negative integer logical tick. The runtime does not read wall-clock time. When an idle instance appears to have been created in the future relative to a supplied tick, it is destroyed rather than reused.
