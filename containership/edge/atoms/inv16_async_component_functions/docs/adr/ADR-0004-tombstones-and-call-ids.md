# ADR-0004: Bounded tombstones and finite call ids

**Status:** accepted (4.3.0).
* Tombstones: FIFO, count-bounded (`tombstone_capacity`, default 65,536 ≈ 7 MiB). Reason-less tombstones are shared
  immutable objects. An id not live, not queued, not in history but below the allocator watermark is
  *issued-but-expired* → `HistoryExpired` (never mistaken for never-issued, never accepted). Replays do not
  refresh retention. History is ephemeral: a restart starts a new generation.
* Call ids: `call_id_bits` wide (default 64), id 0 reserved, strictly monotonic, never wrap within a generation;
  exhaustion fails closed; a near-exhaustion event fires once at 90%. `renew_generation()` (drained instances only)
  resets the counter and clears history; old-generation ids are rejected with `StaleGeneration` when callers pass
  `generation=` (enforced with `require_generation=True`). Encoding: 8-byte little-endian.
