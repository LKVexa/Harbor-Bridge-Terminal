# Incident response (M83)

| Severity | Definition | Response | Page |
|---|---|---|---|
| SEV1 | integrity breach suspected; no hosts; cross-tenant access | 15 min, all hands | primary + backup + security |
| SEV2 | failover SLO burn; auth denial spike; signature refusals | 30 min | primary |
| SEV3 | latency burn; single-tenant degradation | next business day | ticket |

## Integrity {#integrity}
1. `set_mode(frozen)`. 2. `quarantine` affected components/hosts. 3. Verify ledger against anchored head; export decision records for the window. 4. Revoke the signer if a signed-but-malicious artifact is suspected (`TrustPolicy.revoked_signers`). 5. Recover per ROLLOUT.md; post-incident review within 5 business days, recorded in REVIEWS.json.

## Auth {#auth}
Check `REPLAY_DETECTED` / `UNAUTHENTICATED` by principal fingerprint in security logs; revoke suspect principals; confirm identity dependencies are available (fail-closed `UNAVAILABLE` is expected during outages).

Paging integration, named contacts and backups are **not configured** (OWNERSHIP.json placeholders; W-OWNERS).
