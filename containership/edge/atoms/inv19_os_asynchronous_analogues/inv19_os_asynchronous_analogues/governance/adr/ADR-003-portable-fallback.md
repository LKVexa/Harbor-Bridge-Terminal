# ADR-003 — Portable fallback (v1, PROPOSED)
**Decision.** `portable` = `selectors.DefaultSelector` + socketpair wakeup, readiness class, real non-blocking I/O via `ReadinessIO`. It cannot be disabled or quarantined. Engagement is counted (`inv19_fallback_engagements_total{reason}`) and alerted when a fast path was expected.
**Limitations.** No completion semantics; selectors folds ERR/HUP into readable/writable — the follow-up syscall discovers the concrete error. Regular files are always "ready" (no async file I/O on this path).
**Rejected.** Thread-pool blocking fallback (unbounded threads, cancellation impossible mid-syscall).
