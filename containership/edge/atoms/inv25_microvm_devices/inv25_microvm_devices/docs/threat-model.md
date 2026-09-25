# INV-25 threat model (C041, C043, C047, C087)

Assets: the active catalogue (defines guest-visible surface estate-wide), activation history, audit chain,
signing keys. Security objective: **no device or register reaches a guest without a reviewed, approved,
audited catalogue entry.**

| # | Threat (STRIDE) | Actor | Control | Test |
|---|---|---|---|---|
| T1 | Forbidden class smuggled (case/whitespace/confusable) | malicious proposer | closed allow-list, strict grammar | `FuzzTest`, regressions F001/F006/F009 |
| T2 | Unreviewed entry | insider | rationale+reviewer mandatory; separate approver | `ErrorContractTest`, `ActivationTest.test_separation_of_duties` |
| T3 | Silent surface growth | insider / compromised CI | `replace()` + diff + `catalogue.widen` + `surface.widened` audit | `ActivationTest.test_widening_requires_widen_capability` |
| T4 | Spoofed identity | external | signed tokens, issuer/audience/key checks | `AuthnTest` |
| T5 | Replay of approved mutation | network attacker | single-use nonces, idempotent candidate IDs | `AuthnTest.test_replay`, `ConcurrencyTest` |
| T6 | Privilege escalation | low-privilege caller | deny-by-default capabilities, env scoping, unknown caps dropped | `AuthorizationTest` |
| T7 | Downgrade (schema / catalogue) | peer / attacker | negotiation floor; rollback only to recorded known-good digests | `CompatTest`, `ActivationTest.test_rollback_restores_exact_digest` |
| T8 | Tampered artifact / state file | supply chain / host | digest+signature binding; state digests re-verified on load | `ProvenanceTest`, `test_tampered_state_refused` |
| T9 | Audit history rewrite | insider | hash chain, append-only sink, verify | `AuditTamperTest` |
| T10 | Resource exhaustion | any caller | ceilings, pre-scan bounds, rate limits, pending cap | `LimitsTest`, `test_rate_limit` |
| T11 | Log/metric injection | proposer | control/invisible chars rejected; redaction | regression F004, `test_redaction` |
| T12 | Parser differential | attacker | strict exact-key parse, duplicate rejection, NaN/Infinity rejection, depth errors caught | `FuzzTest.test_parser_closed_fail` |
| T13 | Guest escape via device register | malicious tenant | minimise surface (ADR-0001); backend hardening is INV-35's | external |
| T14 | Side-channel via device surface | tenant | INV-43 optional peer signal; absence never implies protection | fixture |

Ambient authority (C043): the package opens no sockets, spawns no processes (except the bootstrap
self-test), reads no environment secrets; the only file access is the explicit `state_path` and audit
path supplied by the host. Encryption (C047): the catalogue contains no secrets; transport security
and at-rest encryption of state/audit files belong to the hosting service (EXTERNAL).
