# Threat model (MC-032, C041) — STRIDE over the INV-62 boundaries

Assets: tenant topology (sensitive: reveals estate layout), routing decisions, site coordinator authority,
configuration, keys, audit trail. Adversaries: malicious tenant, compromised workload/scheduler credential,
hostile topology feed, compromised device, network attacker, supply-chain attacker, insider operator.

| ID | Threat (STRIDE) | Vector | Control | Test |
|---|---|---|---|---|
| T01 | Spoofing | forged/tampered credential, unknown/revoked key | PKT1 HMAC, keyring states | `test_T01_*` |
| T02 | Spoofing | expired/future/over-long/wildcard credential | lifetime+skew checks, issue-time guards | `test_T02_*` |
| T03 | Spoofing/Replay | replayed mutating credential (incl. after restart); cache exhaustion | single-use nonce persisted before use, fail-closed cache | `test_T03_*` |
| T04 | Elevation | scheduler mutates graph; operator via wrong role | role matrix, default deny | `test_T04_*` |
| T05 | Elevation | node-agent campaigns for another node | node binding | `test_T05_*` |
| T06 | Info disclosure / Tampering | cross-tenant read or write | tenant scoping, per-tenant graphs | `test_T06_*` |
| T07 | Tampering/DoS | malformed, oversized, deep, NaN, duplicate-key payloads; identifier injection | strict codec + schema + identifier grammar | `test_T07_*`, fuzz |
| T08 | DoS | graph explosion, huge batches | quotas, batch limit | `test_T08_*` |
| T09 | DoS | query flood | per-tenant buckets, in-flight bound | `test_T09_*` |
| T10 | DoS | anonymous flood draining a victim tenant's bucket | admission after authz | `test_T10_*` |
| T11 | Spoofing | hostile feed reports links up/down to steer traffic | hysteresis, flap hold, staleness, quarantine, audit | health + fault tests |
| T12 | Tampering | split-brain / stale leader acting after partition | terms, fencing, quorum, lease revocation on heal | election tests |
| T13 | Tampering | edited/truncated WAL, snapshot, audit | MAC chains, fail-closed start | persistence + audit tests |
| T14 | Info disclosure | secrets/credentials/node names in logs, errors, health | allow-listed fields, redaction, pseudonyms, generic INTERNAL | leakage tests |
| T15 | Repudiation | operator denies freeze/quarantine | audited admin actions | `test_quarantine_*` |
| T16 | Elevation | config disabling auth / inline secrets / unsigned change | const schema, secret refs, signed config | config tests |
| T17 | DoS | dependency outage causing fail-open | fail-closed semantics | outage tests |
| T18 | Supply chain | tampered release artifact | manifest digests + signature verify | `tools/release.py verify` (CI lane) |
| T19 | Side channel | timing on MAC compare | `hmac.compare_digest` | code review |
| T20 | Clock attack | stepping time to revive credentials / drain buckets | skew bound, bucket clamps backward steps | `test_bucket_refills_and_never_negative_on_clock_step` |

Residual risks (tracked in `governance/waivers.json`): transport confidentiality unverified (T-mTLS, MC-021);
ephemeral non-production release signing key; issuer sidecar key custody not implemented here; audit head
anchoring to an external store is an operational procedure, not code.
