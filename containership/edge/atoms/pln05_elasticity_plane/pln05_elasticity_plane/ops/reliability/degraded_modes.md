# PLN-05 degraded and failover modes

| Mode | Entry | Behaviour | Exit | Max authority |
|---|---|---|---|---|
| stale (scope) | demand age > `stale_after_s` | one `stale-input-hold` published; target unchanged | fresh authenticated in-order sample → `recovery` | current target |
| degraded (scope) | demand age > `degraded_after_s` | one `degraded` hold published | same as stale | current target |
| security-degraded (plane) | audit buffer ≥ 75 % or no active key | scale-up refused (`R_DEGRADED_NO_SCALE_UP`); scale-down allowed | pressure < 75 % | current target |
| no-lease | coordination lost past lease expiry | no decisions (`E_NOT_LEADER`); consumer keeps last target | lease re-acquired (new epoch) | none |
| sink breaker open | ≥ `breaker.failure_threshold` publish failures | decisions persisted, not delivered | half-open probe succeeds | unchanged |
| telemetry loss | log/trace sink failures | none (counted only) | — | unchanged |

**Failover:** only *controller ownership* fails over (lease → peer instance, epoch+1, fencing). **Consistent failover requires a shared (or replicated) `state_dir`:** every writer of a scope — demand decisions, limits, ceiling lowering, controls, resume — must hold that scope's lease, and an instance that starts a *new* lease term reloads the scope from shared state before acting, so envelopes, idempotency ids, source sequences and controls carry over. Tenant-wide controls live in their own leased record and are re-read whenever the file changes. Without shared state a peer can take over leadership but starts from the envelope PLN-01 re-declares. After a wall-clock step backwards the local lease view is distrusted and every call re-verifies with the coordination service. Demand sources and providers are not failed over by PLN-05; an alternate demand source is simply another authenticated reporter, never of higher trust. Residency and isolation are unaffected by failover because scopes, credentials and envelopes are identical on every instance, and the peer must hold the same key ring. Flapping dependencies are debounced by the breaker cooldown (with jitter) and reported as `R_FLAPPING_*` without toggling readiness. A failover target that rejects a publication leaves the decision persisted; `republish_last` re-emits it idempotently.

**Prolonged degraded operation (operator):** check `status` (admin) for `mode_reason`; if demand is lost > 30 min, freeze the scope to make the hold explicit, open an incident with the GAP-09 owner; do not raise ceilings manually.
