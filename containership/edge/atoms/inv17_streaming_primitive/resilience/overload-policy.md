# INV-17 Overload / Load-Shedding / Circuit-Breaker Policy

**Controls:** C054 (with C052 health thresholds)
**Owner:** UNASSIGNED — owner to fill

## Layered defences (in evaluation order for `control::StreamRegistry.write`)

| # | Check | Outcome | Error code | Counted as |
|---|---|---|---|---|
| 1 | `_gate`: component disabled / scope frozen | Reject | `PK_STREAM_DISABLED` | — |
| 2 | Token verification | Reject | `PK_STREAM_AUTH*`, `PK_STREAM_TRUST_UNAVAILABLE` | audit event |
| 3 | Tenant buffered >= `TenantQuota.max_buffered` | Shed | `PK_STREAM_QUOTA` | `shed_count` (`inv17_load_shed_total`) |
| 4 | Instance buffered >= `global_buffer_budget` | Shed + `breaker.failure()` | `PK_STREAM_LOAD_SHED` | `shed_count` |
| 5 | `Stream.write`: frozen / type / credit / `max_buffer` | Reject | `PK_STREAM_FROZEN`, `PK_STREAM_TYPE_MISMATCH`, `PK_STREAM_CREDIT_EXHAUSTED`, `PK_STREAM_BUFFER_LIMIT` | `credit_stalls` for no-credit |
| 6 | Success | `breaker.success()` | — | `transferred` |

`StreamRegistry.open` additionally checks `breaker.allow()` (`PK_STREAM_CIRCUIT_OPEN`) and
`max_streams` (`PK_STREAM_QUOTA`, audited `quota.denied`).

## Circuit breaker (`control::CircuitBreaker`)

- `closed` -> `open` after `threshold` (default 5) consecutive failures.
- `open` -> `half_open` when `cooldown` (default 5 s) elapsed at the next `allow()`.
- `half_open` + failure -> `open`; any success -> `closed`, failures reset.
- Only global-budget sheds count as failures; the breaker gates **new opens**, not writes to open streams.
- Exported as `inv17_breaker_open`; reported as degraded health when not closed.

## Backpressure vs shedding

Credit exhaustion is normal backpressure, not overload: `write` raises `CreditExhausted` and the
scheduler (outside INV-17) decides when to retry. `write_wait` blocks with timeout/cancellation.
Shedding errors mean "retry with backoff"; INV-17 does not retry internally.

## Health thresholds (`control::HealthPolicy`, defaults)

`stall_ratio_degraded` 0.25, `stall_ratio_unhealthy` 0.75 (after `min_attempts` 20),
`stall_seconds_unhealthy` 30 s continuous credit stall with at least one stalled write,
`buffer_fill_degraded` 0.9 of `max_buffer`. `status()` reports `ready=False` when `unhealthy` or `disabled`.

## Known limitations

- Direct `Stream.write` bypasses layers 3–4.
- Tenant sum of quotas may exceed global budget (oversubscription is permitted).
- Breaker configuration values in `config/*.json` are not wired (see `deployment/tier-profiles.md`).
- `buffered_total` is O(streams) per write.

Tests (planned): `tests/test_control.py`, `tests/test_fault_injection.py`, `tests/test_soak.py`.
