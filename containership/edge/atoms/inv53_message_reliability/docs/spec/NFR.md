# Non-functional requirements (C013)

Targets are **PROPOSED** until an owner approves them. "Measured" cites the 5.1.0 CI evidence.

| Id | Property | Requirement | Verification | Status |
|---|---|---|---|---|
| NFR-D1 | Durability | An acknowledged `put` (OK) survives process crash and power loss when `fsync=true` | `test_durable.py` crash/replay suites | Met locally; storage media not qualified |
| NFR-D2 | No loss | Every accepted id is ready, in flight, dead-lettered or acked — never absent | `test_property_concurrency.py::PropertyTest` | Met (model-based, 40 seeds + crash-anywhere 30 seeds) |
| NFR-C1 | Consistency | Durable queue and reference model agree on every counter for identical op sequences | `test_durable_equals_reference_model` | Met (25 seeds) |
| NFR-F1 | Fencing | Stale/late/superseded lease tokens never settle; a superseded writer never appends | T4, epoch-fencing tests | Met single-host; cross-host BLOCKED |
| NFR-I1 | Isolation | No request can read or settle another tenant's messages | `test_T2_cross_tenant_…` | Met at the broker boundary |
| NFR-A1 | Availability | Storage failure degrades to refusals (breaker), never to silent loss; recovery by replay | `test_storage_failure_opens_breaker…` | Met locally |
| NFR-R1 | Recovery | Restart replays the journal; torn tail truncated; corruption refuses to open | durable suite | Met |
| NFR-P1 | Latency | durable put/ack/receive p99 ≤ 5 ms (fsync off), ≤ 10 ms (fsync on) on reference hardware | `perf/THRESHOLDS.json` | PROPOSED; reference hardware not named |
| NFR-DT1 | Determinism | Same seed + same logical clock ⇒ same state digest | property + bench seeds | Met |
| SLO-1 | Redelivery | A message held by a crashed consumer becomes visible within `visibility_seconds` of lease start | contract tests | Met |
| SLO-2 | Poison | A poison message is delivered at most `max_attempts` times then dead-lettered | contract tests | Met |
| SLO-3 | Settlement | Only the current lease may settle | T4 | Met |
