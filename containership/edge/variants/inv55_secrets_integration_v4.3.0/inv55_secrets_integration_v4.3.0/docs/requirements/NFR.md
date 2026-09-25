# Non-functional requirements

| ID | INV55-NFR | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

**Figures are TARGETS.** Where a single-host measurement exists (`evidence/benchmark_baseline.json`) it is quoted in the Basis column; none are fleet or production measurements.

| ID | Category | Target | Basis |
|---|---|---|---|
| INV55-NFR-001 | Availability | 99.9 % monthly of requests not failing with INTERNAL/AUDIT_UNAVAILABLE/FROZEN (excluding provider outages) | proposed |
| INV55-NFR-002 | Latency, cached resolve+use | p50 < 1 ms, p99 < 5 ms (contract SLO), max < 50 ms | Single-host benchmark: met sequentially (p99 0.50 ms), NOT met at 16 threads (p99 21.4 ms) — WVR-030 |
| INV55-NFR-003 | Latency, provider resolve | p50 < 20 ms, p99 < 250 ms, max bounded by `request_timeout_s` = 2 s | proposed |
| INV55-NFR-004 | Latency, use | p99 < 5 ms (audit fsync dominates with `FileAuditSink`) | proposed |
| INV55-NFR-005 | Durability, audit | Record fsynced before acknowledgement; zero acknowledged ops without record | `FileAuditSink`, `_audit` (implemented) |
| INV55-NFR-006 | Durability, broker state | Scopes/retirements durable per instance with `state_path` (fsync + atomic replace); leases/cache/idempotency volatile by design | crash-restart-semantics.md |
| INV55-NFR-007 | Consistency | Read-your-writes within a process; cross-instance staleness <= `cache_ttl_s` (30 s) for versions; retirements not propagated | split-brain.md |
| INV55-NFR-008 | Isolation | Zero cross-tenant resolutions; zero secret values in logs/errors | contract SLOs "no budget" |
| INV55-NFR-009 | Startup | `start()` completes within one provider health call (< 2 s) | `SecretsService.start` |
| INV55-NFR-010 | Recovery | RTO: process restart < 5 min (scopes reload from state file); RPO for audit: 0 acknowledged records | proposed |
| INV55-NFR-011 | Throughput | >= 1 000 cached resolve+use/s per process | Single-host benchmark: 4 330/s sequential, 1 834/s at 16 threads |
| INV55-NFR-012 | Resource | Memory bounded by limits in interface-limits.md; cache unbounded by count (gap) | `ServiceLimits` |

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Benchmark results quoted |
| 4.3.0 | 2026-09-22 | Durable control state |
