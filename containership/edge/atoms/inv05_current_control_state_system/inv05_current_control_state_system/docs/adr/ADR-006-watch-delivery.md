# ADR-006 — Watch delivery: live queue with lossless history fallback

* Status: **Proposed** · Traceability: C025, C054, C067, MC-014, MC-015, MC-017

Watches start in catch-up mode (paged reads from retained history) and switch to live mode atomically under the store lock. When a live queue would overflow, the watch falls back to history paging instead of dropping events. A watch is cancelled only when compaction overtakes it (`CSTATE_COMPACTED` → relist) or it lags the head by more than `max_lag` revisions (`CSTATE_SLOW_CONSUMER` → resume/relist), so one dead consumer cannot pin compaction forever. Progress frames are emitted only in live mode with an empty queue, reading the head under the store lock, so a progress revision is always a safe resume point.
