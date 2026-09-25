# Failure catalog, detectors and thresholds (MC-036)

| Level | Failure | Detector | Threshold | Automatic response | Operator response |
|---|---|---|---|---|---|
| Process | handler hangs | `Watchdog.stalled()` → `health.ready=false` | op in flight > `max_deadline_s` | readiness drops; LB drains | inspect stalled_ops, restart |
| Process | crash mid-write | journal replay at start | torn tail | discard tail, continue | none |
| Process | journal interior corruption | replay checksum | any | refuse to start | restore from backup (BACKUP_RESTORE.md) |
| Adapter | backing store down | `PK_ADAPTER_UNAVAILABLE`, breaker | N consecutive failures | breaker open; degraded buffering if enabled | check INV-49 adapter |
| Adapter | suspected hostile | operator | — | — | `quarantine_adapter` |
| Node | lease lost | `LeaseManager` / `Fenced` | lease expiry | stale writer fenced | fail over |
| Site | partition | adapters unavailable | breaker open on all adapters | degraded/read-only | SEV2 |
| Site | residency-safe target absent | `select_failover` | none eligible | read-only | SEV2 |
| Control plane | config invalid | `config.validate` | any | activation refused; previous revision stays active | fix and re-activate |
| Security | time/revocation unavailable | `SecurityDependencyUnavailable` | any | fail closed | SEV2 + PLN-07 |
| Security | audit chain break | `verify_chain` | any | — | SEV1 |
| Capacity | load shedding | `PK_RATE_LIMITED` rate | > 1 % of calls for 5 min | — | scale / quota review |
