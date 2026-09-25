# Disconnected / intermittent-network behaviour (MC-019, MC-054, MC-085)

| Situation | Admission | Running instances | Stop / quarantine |
|---|---|---|---|
| Trust root fresh | normal | normal | normal |
| Trust root refresh failing, cached copy within `max_age_hours` | allowed from the cached root | unaffected | allowed |
| Cached root older than `max_age_hours` | **refused** (`UK_TRUST_UNAVAILABLE`, retryable) | keep running on their verified seal (fail static) | allowed |
| Revocation published while offline | takes effect on the next successful refresh; the maximum exposure is `max_age_hours` | not revoked retroactively; an operator can quarantine by digest | allowed |
| Reconnect | refresh root, recompute health, resume admission | no restart | — |

These rules are implemented in `precedence.disconnected_decision` and `TrustRoot.check_fresh`, and
tested in `test_platform.Precedence` and `test_seal.Signatures`.

Multi-site failover and residency-aware recovery belong to PLN-04 and placement. INV-27 supplies
only the precedence rule (`precedence.resolve`). Certification against a real partition is blocked
on W-FLEET.
