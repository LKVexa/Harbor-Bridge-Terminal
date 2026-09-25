# INV-16 Operator Runbook (v4.3.0)

Every alert in `ops/alerts.yaml` links to a section here. Metrics are defined in `observability.METRICS`.
Diagnostics: `snapshot()` on the instance, the `inv16.event/1` stream, and `python -m inv16_async_component_functions.preflight --json`.

## R1 Double delivery attempted (`inv16_double_delivery_attempts_total` > 0) — PAGE
1. It is a *rejected* second completion (the runtime refused it); the invariant held. Treat as a caller bug or replay.
2. Pull `double_delivery` events (never sampled) → `call_id`, `trace_id`; find the duplicate producer.
3. If rate is rising, isolate the producing component; do not restart INV-16 (state is correct).
4. Escalate to the owner (docs/OWNERSHIP.md) with the event lines.

## R2 Re-entrancy refusal storm (`rate(inv16_reentrancy_refusals_total[5m])` high)
1. Identify functions from `reentrancy_refused` events (`reason_code`: `stateful_busy` or `queue_full`).
2. Stateful functions refuse by design. Options: raise `queue_depth` (bounded), add instances, or fix the caller retry loop.
3. Never switch a stateful function to `allow` — construction refuses it.

## R3 Saturation (`inv16_concurrency_refusals_total` rising, in-flight at limit)
1. Check `calls_in_flight` vs configured limit and p99 latency; use `bench/capacity.json` model to size.
2. Scale out instances (single owner each — ADR-0003) or raise the limit within memory budget.
3. Confirm recovery: in-flight drains to baseline once load drops (tested in test_stress).

## R4 Cancellation storm / trap storm
1. Group `call_cancelled` / `calls_cancelled_batch` by `reason_code`; `deadline` → upstream latency, `disconnect` → client side.
2. `callee_trapped` (never sampled) → callee defect; all its in-flight calls are terminal and late values are rejected.
3. Subsequent calls are admitted without restart (fault tests); if traps repeat, roll back (R7).

## R5 Call-id near exhaustion (`call_id_near_exhaustion` event / `inv16_call_ids_remaining` low)
1. Drain the instance (stop admission, wait, `cancel_all(SHUTDOWN)`).
2. `renew_generation()`; ensure all callers pass `generation=` (`require_generation=True` recommended).

## R6 Late events after history expiry (`inv16_expired_late_events_total` rising)
Late arrivals exceed the tombstone window. Increase `tombstone_capacity` (≈106 B each, see capacity bench)
or fix the delaying layer. They are still rejected (`HistoryExpired`), never accepted.

## R7 Rollback
`python tools/rollback.py` (or `tools.rollback.rollback(instance)`): drains, cancels remainder with
`SHUTDOWN`, downgrades config, starts 4.2.0 behind a generation fence. Record the JSON output with the incident.

## R8 Emergency disable
Remove the component from the registry package; the pk_core gate reports a reduced element count. Keep evidence.

## R9 Telemetry sink failure (`inv16_sink_failures_total` > 0)
Correctness is unaffected (sinks run outside the lifecycle lock). Repair the sink; counters show the gap.
