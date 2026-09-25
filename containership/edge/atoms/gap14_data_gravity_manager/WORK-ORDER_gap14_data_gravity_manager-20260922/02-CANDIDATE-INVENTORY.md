# 02 — Candidate inventory

The yard (ledger + deep map) could not be searched: folder access to `GitHub Junkyard` was denied in this session. No donor parts were pulled; no `THIRD-PARTY-NOTICES.md` is needed (no third-party code in v4.3.0).

| Finding group | Donor | Disposition |
|---|---|---|
| Signed artifacts, key ring, canonical JSON | — | build-new (stdlib `hmac`/`hashlib`/`json`) |
| Estate adapters GAP-13/03/05, SCH-01, PLN-06 | — | build-new |
| Identity / capability tokens | — | build-new |
| Hash-chained audit | — | build-new |
| Signed config lifecycle | — | build-new |
| Resilience (deadline, retry, breaker, admission) | — | build-new |
| Metrics / logs / traces | — | build-new (Prometheus text format, W3C traceparent) |
| JSON-Schema validation | — | build-new subset validator (no `jsonschema` dependency, keeps zero runtime deps) |
| Planner / DAG / drift | — | build-new |

Suggested yard searches for the next session (to confirm there was nothing reusable): `circuit breaker python`, `hash chain audit log`, `jsonschema validator stdlib`, `prometheus exposition python`, `page hinkley drift`, `capability token hmac`.
