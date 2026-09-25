# ADR-004: Trusted wall time = authoritative anchor + local monotonic elapsed
Status: Proposed · Date: 2026-09-22

**Decision.** All freshness/expiry decisions read `TrustedClock.now()`; it refuses before first sync, after `max_unsynced`, and permanently after a skew violation until reviewed. The authenticated time *source* (NTS/Roughtime/PTP) is **not integrated** (blocked: no infrastructure); `sync()` is the integration point.
**Links.** TH17 · `mc/clock.py`.
