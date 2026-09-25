# Resilience and failure handling (INV30-GAP-033..039 · INV-30-C051–C060, C089)

## Failure inventory (C051)
| Failure | Detection | Behaviour |
|---|---|---|
| backend error/outage | exception code dependency | circuit breaker (5 failures → open 10 s → half-open) → `CIRCUIT_OPEN`; health `degraded` |
| overload | admission | `OVERLOADED` (retryable), per-tenant token bucket fairness |
| stall | StallDetector: work in flight & no progress 5 s | health `stalled`, not ready → orchestrator restarts |
| process crash | supervisor | restart → volatile table empty → all handles `NOT_FOUND` (fail-safe) |
| duplicate controller | lease epoch | stale instance refuses mint/derive (`DISABLED`) |
| discovery unavailable / partition | GAP-02 `unprobed` | tier unavailable; hardware workloads refused |
| key/secret service unavailable | secret resolve error | refuse to start (`CONFIG_INVALID`) |
| time skew | auth | requests outside ±30 s refused |
| telemetry sink down | non-critical | degraded; bounded in-memory buffers drop oldest |

## Health thresholds (C052): stall 5 s; breaker threshold 5; saturation alert ≥ 0.8 for 5 min.
## Retry (C053): only codes with `retryable=true`; full jitter; 4 attempts; never security codes.
## Failover (C055): to another node only if its GAP-02 report says `present` for hardware workloads; never across
residency boundary; never to model for hardware workloads.
## Degraded (C056): telemetry export, decision log persistence, and remote attestation refresh are non-critical.
## Quarantine/freeze/disable (C059): tenant quarantine, service quarantine (invalidate-only), emergency disable
(revokes everything) — `service.py`, `ops.py`.
## Tests (C060, C089): `tests/test_resilience.py` injects backend outage, breaker recovery, stall, restart,
duplicate controller, discovery partition/reconnect, secret-service loss.
