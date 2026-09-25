# ADR-002: Hash-chained WAL store for security state; replay retention by TTL window
Status: Proposed · Date: 2026-09-22

**Context.** v4.2.0 held all state in memory; restart reopened replay (MISSING_COMPONENTS #7).
**Decision.** `DurableStore`: fsync'd write-ahead log with per-record hash chain, atomic snapshots, torn-tail truncation, restore with a monotonic generation floor. Nonces are only acceptable while *outstanding*, so spent records may be pruned after `expiry + skew_margin` without reopening replay (argument in `mc/replay.py`).
**Options.** SQLite (rejected for this archive: owner's yard rule forbids SQLite on the mounted yard, and it would still need the same replay argument); etcd/Spanner-class consensus store (the right production answer — **blocked**, no infrastructure).
**Consequences.** Single-writer only; multi-process/multi-replica safety is simulated with a lease/fencing token over one store. Whole tables are held in memory; `items()` copies are O(n) — a scale limit recorded in `docs/CAPACITY.md`.
**Links.** TH02, TH03, TH19 · `mc/store.py`, `mc/replay.py`.
