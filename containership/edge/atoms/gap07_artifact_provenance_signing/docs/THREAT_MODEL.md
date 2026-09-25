# GAP-07 threat model (STRIDE + LINDDUN-lite), v6.0.0

**Assets:** artifact admission decisions; release and config-authority signing keys; trust generations; policy
bundles; the audit chain; trusted time; transparency checkpoints.
**Trust boundaries:** (B1) KMS/HSM ↔ signer workload, (B2) control plane ↔ relay/cache ↔ site, (B3) registry ↔
verifier, (B4) verifier ↔ runtime handoff, (B5) exporter ↔ audit store, (B6) time authority ↔ site.

| # | Threat (STRIDE) | Boundary | Mitigation (code) | Residual / external |
|---|---|---|---|---|
| T1 | Spoof signer by replaying a valid signature to another kind, environment, tenant or policy domain (S) | B3 | every context field is bound in `ld_encode("signature/3")`; verifier checks each (`signing.verify_signature`) | — |
| T2 | Algorithm substitution/downgrade (T) | B3 | explicit `alg` = certified alg, authz set + min strength, key-type match (`algorithms`) | — |
| T3 | Signer key compromise (S, E) | B1 | HSM non-exportable custody, pinned SPKI, urgent revocation delta, blast radius + quarantine (`compromise`) | detection latency depends on estate SOC |
| T4 | Alias redirect / KMS returns another key (T) | B1 | version pinning + post-sign verification under pinned SPKI (`ResilientCustody`) | — |
| T5 | Config-authority compromise, i.e. malicious trust/policy (E) | B2 | separate authority keys with purpose sets; monotonic generations; audit; **single authority is a residual risk**: M-of-N config signing is recommended (ADR-005) | open |
| T6 | Relay rollback / freeze of trust (T, D) | B2 | signature + generation + parent + expiry checked locally; staleness → not ready (`distribution`) | a freeze can delay revocation up to the staleness budget |
| T7 | Rollback to an older persisted state after crash or restore (T) | host | monotonic floor file, 2-party stale restore (`store`) | floor file on the same disk; TPM NV counter recommended |
| T8 | Clock rollback extends validity (T) | B6 | signed time attestations, sequence anti-replay, persisted floor, jump detection (`timesrc`) | an RTC reset needs operator recovery |
| T9 | Parser attacks: duplicate keys, deep nesting, big ints, Unicode (T, D) | all | `canonical.strict_loads` bounds and rejections; size limits before crypto; fuzz suite | — |
| T10 | Tag mutation / manifest substitution / partial read (T) | B3 | digest-only admission, descriptor size + digest verification, referrers by `subject` (`registry`) | live registry auth is estate-side |
| T11 | TOCTOU between verify and execute (T) | B4 | `handoff()` re-hash + trust-digest check | the runtime must load only handoff bytes |
| T12 | Split-view / equivocating transparency log (R, T) | B3 | local inclusion + consistency proofs, monotonic cache, `compare_views` monitor | needs ≥ 2 independent monitors |
| T13 | Audit history rewrite after node compromise (R) | B5 | hash chain + append-only sink + periodic anchoring into an independent log; `verify_export` | WORM storage configuration is estate-side |
| T14 | Admission DoS / amplification (D) | B3 | tenant token bucket, bounded concurrency + queue → `OVERLOADED` deny; bounded parsers; cached decisions | — |
| T15 | Cross-tenant confusion (I, E) | all | namespace in kid, certs, generations, requests, time attestations; `TENANT_MISMATCH` | — |
| T16 | Waiver / break-glass abuse (E) | policy | signed, scoped to a digest, ≤ 30 d / ≤ 24 h, 2 approvers ≠ owner, non-waivable signature/threshold, single-use nonce, audited | human collusion |
| T17 | Secret leakage via logs/metrics (I) | all | no API returns private keys; `telemetry.redact`; label allowlists; exporter refuses secret-bearing events | — |
| T18 | Insider operator bypass (E) | ops | no bypass API; break-glass only; drift test for the webhook `failurePolicy` | organisational |
| T19 | Side channels in crypto (I) | B1/B3 | only `cryptography`/OpenSSL primitives; constant-time compares for digests | library-level |
| T20 | Privacy / linkability of workload identities in audit (LINDDUN) | B5 | identity URIs are workload, not personal; redaction rules; retention policy in RUNBOOKS | data-protection review estate-side |

Abuse cases are exercised in `tests/test_v6_*`. Unmitigated residuals (T5 single config authority, T7 floor
without hardware counter, T13 WORM configuration) are tracked in `MISSING_COMPONENTS.md`.
