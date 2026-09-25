# INV-21 Threat Model (STRIDE-oriented)

Assets: tenant isolation, authorization decisions, residency authority, trace/audit integrity, host resources.

| ID | Threat | Mitigation (code) | Test |
|---|---|---|---|
| T1 | Tenant/principal spoofing via payload, strings or a hand-built `Principal` | production re-derives the principal from the carried credential with the chainer's own `IdentityVerifier` and refuses any mismatch; 4.x API refused | `T1`, `test_identity_context`, `SP01` |
| T2 | Credential replay | expiry + skew bound, key retirement, peer `max_token_age_s` (default 300 s), TLS off loopback; `single_use` available for root calls. Bearer tokens are multi-hop by design, so replay *within* the age window by a party that captured the token is a residual risk (needs channel binding / mTLS, ADR-005) | `T2`, `IdentityTest`, `SP10` |
| T3 | Path/depth reset or caller spoofing via `path` | peer re-applies depth/cycle to supplied path; only chainer-sealed child contexts (HMAC seal bound to an active root call) count as nested hops or supply the policy `caller` | `T3`, `SP02`, `SP03` |
| T4 | Injection via identifiers | strict identifier grammar, no silent normalisation on production API | `T4` |
| T5 | Resource exhaustion (depth, fan-out, body size, telemetry, audit memory) | depth cap, admission, 1 MiB body cap, bounded rings, bounded label cardinality | `T5`, `test_concurrency` |
| T6 | Compromised/faulty capability provider | `GuardedProvider` type/schema/correlation/revision checks, fail closed | `T6`, `PolicyTest.test_fail_closed_matrix` |
| T7 | Malicious peer response | schema-validated response, unknown codes → protocol error, recursion-bomb safe | `T7` |
| T8 | Side channel through error detail | public envelope allow-listed keys, clipped messages, diagnostics protected | `T8`, `ErrorTaxonomyTest` |
| T9 | Stale controller / split-brain placement | epoch arbitration, tenant ownership, leases | `T9`, `ResidencyTest` |
| T10 | Rogue issuer / unsigned principal | issuer allow-list, provenance check | `T10` |
| T11 | Timing attacks on MAC compare | `hmac.compare_digest` everywhere | `T11` |
| T12 | Audit tampering (edit, delete, reorder, truncate) | HMAC hash chain + externally exported head | `T12`, `AuditTest` |

Residual risks (not mitigated here): **in-process handlers are inside the trust boundary** — code running in the chainer's interpreter can read private state (hop-seal key, verifier keys) and spoof a policy caller or leak a sealed context during its own root call (follow-up audit); isolation requires the INV-20 component sandbox; bearer-token replay within `max_token_age_s` (needs mTLS/channel binding); hardware/workload attestation of the calling component (needs estate attestation service); key distribution and rotation cadence (KMS); denial of service below the admission layer (OS/network); side channels inherent to co-residency (CPU caches) — out of scope for a call-path component and recorded in `governance/waivers.json`.
