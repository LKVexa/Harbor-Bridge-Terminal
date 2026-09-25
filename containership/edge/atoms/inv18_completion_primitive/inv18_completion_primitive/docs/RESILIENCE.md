# INV-18 resilience specification (C051–C060)

## 1. Failure-mode matrix (C051)

| Failure | Detection | Impact | Containment | Recovery | State consequence | Test / N/A |
|---|---|---|---|---|---|---|
| component exception (bad input) | structured code | caller only | exception, state unchanged | caller fixes input | none | test_future, test_errors |
| producer crash | ResolverCap finaliser | receiver gets FUTURE_ABANDONED | per future | none needed | future ABANDONED | fault: producer_crash |
| consumer crash | value never taken | memory held until process exit | bounded by limits | restart releases | leaked entry, counted in outstanding | fault: consumer_crash |
| process crash / restart | host supervisor | all pending futures lost | process | restart; peers see new boot epoch | nothing survives (non-durable by design) | test_resilience RestartTest |
| runtime/interpreter failure | host | as process crash | process | restart | as above | RestartTest |
| VM/container, node, site loss | host / orchestrator | as process crash | outside INV-18 | higher layer re-creates work | as above | N/A for a process-local library (higher-layer responsibility) |
| network partition (adapter) | client retry exhaustion | remote calls fail DEPENDENCY_UNAVAILABLE | adapter | reconnect, idempotent resend | no duplicates | DistributedTest |
| dependency loss (telemetry sink) | sink exception | logs dropped | counted, DEGRADED | sink restored | none | fault: telemetry_failure |
| pk_core failure/absence | import error | audit integration unavailable | lazy import | pin pk_core | none (core unaffected) | test_security AuthorityTest |
| control-plane / key service failure | KeyRing unavailable | wire calls refused | fail closed | restore service | none | OutageTest |
| provider failure | — | — | — | — | — | N/A: no provider dependency |
| configuration corruption | validation | activation refused | old revision stays active | fix config / rollback | none | test_config |
| artifact corruption | SHA256SUMS / verify | release refused | gate | re-release | none | IntegrityTest |
| resource exhaustion | admission | RESOURCE_EXHAUSTED | per request | release futures | none | fault: resource_exhaustion |
| clock anomaly | monotonic clock only | latency/age telemetry skew | telemetry only | none | none — correctness is clock-free | test_runtime ClockTest |

## 2. Health and stall detection (C052)

`HEALTHY` no reasons; `READY` = not FAILED and not component-disabled; `DEGRADED` with
reasons `DISABLED, SOFT_LIMIT_EXCEEDED, STALLED_FUTURES, TELEMETRY_SINK_UNAVAILABLE`;
`FAILED` on any invariant violation. A future is *stalled* when pending longer than
`stall_threshold_s` (default 30 s: the p99.9 of expected producer latency in the
adjacent async layer is an application property, so the value is configuration, not
a constant). A stall only degrades status when > `stall_ratio_degraded` (10 %) of pending
futures **and** at least 3 are stalled — one slow producer or a short spike is
application delay, not a primitive malfunction. Pending-age p50/max are reported.
Thread starvation in adapters is visible as rising pending age with low CPU.

## 3. Bounded retries (C053)

Local transitions are never retried (non-idempotent). Adapter operations retry with
`retry.RetryPolicy`: max attempts (default 3), full-jitter exponential backoff, cap per
delay, total budget, deadline and cancellation honoured, only for retryable codes, only
with idempotency keys. Retry metrics: `attempts_made`; callers log them.

## 4. Admission, load shedding, circuit breaking (C054)

Saturation signals: outstanding vs soft/hard limits, per-tenant counts. New work is
rejected at the hard limit; admitted futures are never affected. Load-shed priority:
tenants over quota first (tenant limit), then everyone (process limit). Circuit breaker
(`retry.CircuitBreaker`) protects adapter calls to external dependencies: closed → open
after N failures, open → half-open after `circuit_reset_s`, half-open → closed only after
`circuit_close_successes` consecutive successes (hysteresis).

## 5. Failover (C055) and split brain (C058)

Local future state is **not** failover-capable; failover is a higher-layer
responsibility. For the wire adapter the creating endpoint is the single authoritative
owner; failover is expressed by raising the ownership epoch (`fence`). The old owner's
epoch is then rejected (STALE_EPOCH), so two writers can never both resolve. Futures stay
bound to their tenant and endpoint (residency). Duplicate controllers are detected by
epoch mismatch; delayed duplicates are absorbed by idempotency keys.

## 6. Degraded operation (C056)

Critical dependencies: none at runtime. Noncritical: telemetry sink, log exporter,
optional diagnostics, pk_core (audit only). Their failure never changes a
resolve/take outcome; status becomes DEGRADED with a reason. Security controls are never
silently dropped: authentication has no noncritical path.

## 7. Crash / restart / replay (C057)

A local future does not survive process restart. Unresolved → lost (receivers in the
same process are gone too). Resolved-not-consumed → lost. Consumed → already released.
Adapters rebuild nothing; a restarted endpoint has a new boot epoch and an empty
registry, so any pre-restart message is refused (PERMISSION_DENIED for unknown futures).
If durability is ever added it requires a new ADR and persistence encryption (C047).

## 8. Quarantine / disable (C059)

`Runtime.disable(admin_cap, scope="component"|"tenant:<id>", mode="drain"|"freeze")`.
Drain: refuse new futures; existing ones resolve and deliver. Freeze: also refuse
mutations; resolved values can still be taken so receivers are not silently orphaned.
AdminCap required; audited; visible in status; reversible with `enable`.

## 9. Fault injection (C060, C089)

`fault.py` runs 9 deterministic scenarios (producer crash, consumer crash, dependency
exception, delayed scheduling, resource exhaustion, configuration failure, telemetry
failure, adapter network loss, duplicate/out-of-order delivery) and checks invariants
after each. Results: `evidence/fault_results.json`. Recovery objectives: every scenario
recovers without restart; zero double resolutions/takes; registry accounting exact.
