# Failure-mode matrix (M17 / M26, C051)

| Failure | Detection | Behaviour | Test |
|---|---|---|---|
| Host process crash | restart | WAL replay restores non-revoked links; torn tail discarded | F01, F02 |
| State corruption | checksums | refuse to start (STATE_CORRUPT); restore from backup | F03 |
| Backend down | health dep + errors | readiness false, breaker opens, retryable 503 | F06 |
| Backend slow | deadline | 504 DEADLINE_EXCEEDED, pool bounded | F07 |
| INV-55 down | resolver | fail closed SECRET_UNAVAILABLE | F08 |
| Key unavailable | keyring | KEY_UNAVAILABLE, no plaintext fallback | F09 |
| Network partition (old owner alive) | lease expiry | new owner takes epoch+1; old fenced | F05 |
| Identity/policy plane down | authn/authz | all calls refused (fail closed) | authn/authz tests |
| Node/site loss | registry + failover | residency-constrained target selection | failover tests |
| Overload | admission | 429 OVERLOADED with retry hint; fair per tenant | burst benchmark |
| Restore of stale backup | restore guard | refused unless forced; tombstones win | F04 |
| Split-brain registration | registry epoch | lower/equal epoch refused | registry tests |

**Not exercised:** real network partitions, real multi-site failover, disk-full, clock-skew beyond 30 s.
