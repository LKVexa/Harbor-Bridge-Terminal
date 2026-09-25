# GAP-05 Missing Components After v4.2.0

The following items are not cosmetic enhancements; they are the remaining components needed to turn the hardened in-memory causal model into a production-grade state-replication subsystem.

## P0 - Required before production use

1. **Authenticated replica identity** - mTLS/SPIFFE-equivalent or platform identity binding so a caller cannot merely claim a configured replica name.
2. **Signed/attested write provenance** - cryptographic binding of writer identity, key, value digest, vector, schema version, and issuance metadata.
3. **Trusted monotonic counter allocation** - per-replica durable counter service or equivalent mechanism that prevents a compromised/buggy declared replica from inventing arbitrary vector jumps without detection.
4. **Durable write-ahead log and recovery** - atomic persistence of active frontier, quarantine, resolution records, and dedupe state across process/node restarts.
5. **Crash-consistent snapshots/checkpoints** - checkpoint format, checksums, generation IDs, atomic replace, recovery validation, and corruption handling.
6. **Tenant/environment namespace enforcement** - tenant and environment identity must be part of the state key and authorization boundary, not only contract prose.
7. **Concrete wire schemas** - machine-readable definitions and validators for `PK_REPLICATED_WRITE/1`, `PK_MERGE_RESULT/1`, and `PK_CONFLICT_SET/1`.
8. **Schema/version negotiation** - forward/backward compatibility rules and rejection behavior for unsupported peer schema versions.
9. **Durable deduplication identity** - stable operation/write IDs or durable causal-event indexes so replay detection survives restart and compaction.
10. **Tamper-evident audit ledger** - append-only chained/signed record for accepted, superseded, duplicated, quarantined, and resolved writes.
11. **Bounded audit/quarantine retention policy** - disk quotas, archival/export, pressure signals, and safe refusal semantics without violating write-preservation guarantees.
12. **Encryption and managed key rotation** - protection for replication data and durable state in transit and at rest.
13. **Authorization policy integration** - explicit permissions for write, replicate, inspect conflicts, quarantine, resolve, reconfigure replicas, and recover state.
14. **Atomic configuration/membership store** - versioned replica-set configuration with provenance, compare-and-swap activation, rollback, and consistent membership epochs.
15. **Replica membership-change protocol** - safe add/remove/reseed behavior that defines how vectors and historical counters are treated across topology changes.
16. **Production conflict-resolution adapter** - integration with the external policy owner (`GAP-13`) including policy version, decision evidence, retries, timeouts, and safe unavailable behavior.

## P1 - Required for reliable distributed operation

17. **Anti-entropy/reconciliation engine** - periodic peer comparison and repair (for example digest/Merkle/range reconciliation) to prove eventual delivery of missing writes.
18. **Replication transport adapter** - authenticated transport, framing, flow control, backpressure, retry, batching, and peer health integration while keeping transport semantics outside the model.
19. **Delete/tombstone semantics** - causal deletes, resurrection prevention, tombstone retention, garbage-collection safety, and restore behavior.
20. **Vector compaction strategy** - dotted version vectors/version-vector compression or epoch-based compaction to bound metadata as replica history grows.
21. **CRDT/commutative type registry** - actual deterministic merge functions for declared commutative value types; the current model keeps concurrency open rather than implementing CRDT merges.
22. **Quarantine operator API** - enumerate, inspect, export, freeze, resolve, retry, and audit overflow conflicts without mutating internal lists directly.
23. **Immutable/read-only state views** - replace or wrap public mutable `siblings`, `discarded`, and `quarantine` collections so callers cannot violate invariants out of band.
24. **Persistence migration framework** - format versions, migrations, downgrade constraints, compatibility checks, and rollback plan.
25. **Backup/restore/reseed workflow** - tested restore from snapshots/WAL plus rejoin semantics and stale-state fencing.
26. **Observability package** - metrics for apply outcomes, frontier width, quarantine depth, resolve latency, replay rate, vector size, persistence lag, anti-entropy lag, and resource saturation.
27. **Structured logs/tracing** - trace context, stable tenant/site/key-operation IDs, redaction rules, sampling, and correlation with policy/transport decisions.
28. **Health/readiness endpoints** - dependency state, durable-store state, schema compatibility, membership epoch, backlog, quarantine pressure, and recovery mode.
29. **Admission control/backpressure** - rate/fan-out controls for conflict floods, hot keys, replay storms, oversized vectors, and recovery bursts.
30. **Resource limits** - maximum vector entries, key/value sizes, unresolved writes, audit growth, batch sizes, and tenant-level quotas.
31. **Time-independent expiry semantics** - if retention/TTL is introduced, define how wall-clock-dependent lifecycle decisions coexist with causal ordering.
32. **Split-brain fencing** - membership epochs/leases/fencing tokens preventing obsolete controllers or removed replicas from continuing to author accepted writes.

## P1 - Test and certification gaps

33. **Fuzz tests** - malformed serialized writes, oversized vectors, duplicate fields, invalid Unicode, schema downgrade attempts, and corrupt persisted state.
34. **Property-based causal tests** - larger randomized histories proving convergence, causal maximality, resolution dominance, and replay invariants beyond the included finite permutation test.
35. **Process-crash fault injection** - kill/restart at each persistence boundary and prove no accepted write is silently lost.
36. **Network partition/reconnect integration tests** - multi-process/site exercises with delayed, duplicated, reordered, and dropped transport frames.
37. **Membership churn tests** - add/remove/reseed replicas while writes are concurrent.
38. **Security tests** - spoofed identities, forged signatures, counter rollback/jump, replay, audit tampering, privilege escalation, and key-rotation failure.
39. **Soak/burst/fleet benchmarks** - latency percentiles, throughput, memory growth, vector growth, quarantine pressure, and recovery rates at realistic scale.
40. **Compatibility matrix** - supported Python/runtime, storage format, wire schema, policy adapter, transport adapter, and neighboring subsystem versions.

## P2 - Operability and scale maturity

41. **Hot-key sharding/partitioning strategy** - avoid one lock/state object becoming a bottleneck for heavily contended keys.
42. **Batch apply API** - transactional/deterministic application of replication batches with per-item outcomes and bounded memory.
43. **Zero-copy/binary encoding path** - reduce serialization/copy overhead for large replication streams after schemas are finalized.
44. **Conflict analytics** - conflict-rate attribution, top hot keys, site-pair patterns, policy outcomes, and recurrence detection.
45. **Administrative tooling/UI** - safe human review of conflicts/quarantine with explicit policy version and audit trail.
46. **Capacity model and release regression gates** - p50/p95/p99/worst-case thresholds, saturation models, and automated performance regression blocking.
47. **Runbooks and incident automation** - paging thresholds, severity mapping, containment/freeze, quarantine draining, reseed, restore, and post-incident verification.
48. **Formal invariant specification/model checking** - TLA+/PlusCal/Alloy or equivalent model for causal frontier, overflow, resolution, and membership-epoch invariants.
49. **Packaging/CI/release metadata** - `pyproject.toml` (or platform equivalent), dependency pinning, reproducible build, SBOM, provenance/signing, CI gates, and release artifact checksums/signatures.
50. **Missing master-prompt evidence artifact** - the previous README referenced `MASTER.md`, but it was absent from the supplied archive. Restore the authoritative artifact if it is required for the series' audit chain; do not reconstruct it from inference.
