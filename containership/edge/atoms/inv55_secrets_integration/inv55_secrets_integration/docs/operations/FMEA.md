# Failure-mode catalog / FMEA (checklist #51)

S = severity, O = occurrence, D = detectability (1 best … 10 worst). RPN = S×O×D.

| ID | Failure mode | Effect | Detection | Response | S | O | D | RPN |
|---|---|---|---|---|---|---|---|---|
| F-01 | provider unavailable | resolves fail RETRYABLE | breaker, `ready=false` | retry/backoff, failover reads | 6 | 4 | 2 | 48 |
| F-02 | provider sealed | same | health `sealed` | Vault unseal (external) | 6 | 2 | 2 | 24 |
| F-03 | slow provider | deadline exceeded | latency histogram | deadline, breaker | 5 | 4 | 3 | 60 |
| F-04 | IdP key rotated without overlap | all UNAUTHENTICATED | failure metric by reason | add both kids | 7 | 3 | 2 | 42 |
| F-05 | clock rollback | CLOCK terminal errors | error code | fix host time, restart | 7 | 1 | 2 | 14 |
| F-06 | lease table full | OVERLOADED | saturation | GC expired, scale out | 5 | 2 | 3 | 30 |
| F-07 | audit sink unwritable | request INTERNAL, no grant | `audit_writable` check | fix volume | 8 | 2 | 2 | 32 |
| F-08 | metric series cap reached | series dropped | `telemetry_series_dropped_total` | review labels | 3 | 2 | 2 | 12 |
| F-09 | config invalid | not activated | stage error | fix and restage | 4 | 3 | 1 | 12 |
| F-10 | process crash | leases lost | restart count | clients re-resolve | 4 | 3 | 2 | 24 |
| F-11 | replica stale during failover | older version served | failover event | failback | 6 | 2 | 4 | 48 |
| F-12 | memory disclosure of plaintext | exposure | none in-process | isolation (W-005) | 9 | 1 | 9 | 81 |
