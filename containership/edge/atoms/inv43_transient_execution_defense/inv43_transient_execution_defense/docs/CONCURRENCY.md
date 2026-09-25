# Concurrency model (item 27, C086)

- `MitigationState`: every public method holds an `RLock`; `report()` and `may_cotenant()` evaluate one `snapshot()` so a decision never mixes two posture versions. **Defect found by this pass:** `report()` computed `total_cost_percent` from a second snapshot, so a concurrent writer produced reports whose total disagreed with their own per-mitigation costs (2,682 torn reports in 0.4 s). Fixed; `ConcurrencyTest.test_no_torn_reads_during_concurrent_record` guards it.
- `PostureRegistry`: one `RLock` over the node map, epochs, quarantine, freeze and explain store. Envelope verification and authz run outside it; the epoch comparison and the swap run inside it (check-then-act is atomic).
- `KeyRegistry._accept_seq`: sequence acceptance is atomic, so two concurrent submissions of the same envelope yield exactly one acceptance.
- `AuditLog.append`: serialized; the chain stays linear under contention (verified after 8 collectors × 20 submissions + 4 × 100 decisions in parallel).
- `Metrics`, `StructuredLogger`, `TokenBucket`, `CircuitBreaker`, `ConfigStore`: internally locked.
- HTTP server: one thread per connection (`ThreadingHTTPServer`), bounded by the non-blocking in-flight limiter.
- Not provided: multi-process or multi-replica consistency.
