# Constraint precedence (C019)

When constraints conflict, the higher row wins. Every refusal happens before any state change. The broker's *evaluation order* (the `service.py` docstring) is cheapest-check-first and differs from this precedence in one place: integrity is detected when the store is touched, and a store that failed integrity or a write is fail-stopped/frozen, so no later request can override it.

1. **Integrity** — never apply an operation on state that failed verification (`E_CORRUPT`, fail-stop after `E_STORAGE`).
2. **Security** — authentication, authorization, tenant isolation, audit availability (fail closed).
3. **Safety of ownership** — lease fencing and epoch fencing (`E_LEASE_STALE`, `E_EPOCH_FENCED`).
4. **Operator intent** — emergency disable, freeze/quarantine, drain.
5. **Resource bounds** — hard capacity limits.
6. **Fairness** — tenant quotas.
7. **Availability** — load shedding and the storage breaker.
8. **Throughput/latency** — fast paths are only used when they preserve rows 1–7 (see `docs/perf/PERFORMANCE.md`).

Example: a frozen queue refuses an ack even though the ack would reduce load (row 4 over row 7). A tenant
over quota still cannot bypass authentication to reach the shed check (row 2 first).
