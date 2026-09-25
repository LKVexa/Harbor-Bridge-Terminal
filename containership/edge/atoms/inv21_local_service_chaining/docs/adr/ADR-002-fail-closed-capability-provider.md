# ADR-002: Per-hop capability decisions via a guarded authoritative provider, fail closed
Status: PROPOSED · Date: 2026-09-23
Decision: every hop builds a `PK_CAPABILITY/1` request (principal, tenant, caller, callee, operation, capabilities, topology, depth, correlation id); `GuardedProvider` enforces timeout, schema/version/correlation/revision checks and a bounded TTL cache without negative caching; any doubt refuses. Revocation latency = cache TTL unless `invalidate()` is called.
