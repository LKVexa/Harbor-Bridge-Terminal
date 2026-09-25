# INV-32 Threat Model (STRIDE+, v4.3.0)

Owner: **unassigned (BLOCKED WS16)** · Review date: 2027-03-22 · Method: STRIDE + replay + side channels.

## Assets
A1 guest resources · A2 host availability (reserve) · A3 controller authority (lease) · A4 tenant isolation ·
A5 audit integrity · A6 configuration · A7 secrets/keys · A8 provider credentials · A9 software artifacts ·
A10 state store.

## Actors
Malicious tenant, compromised guest, compromised controller, malicious operator, compromised dependency,
supply-chain attacker, network attacker, stale controller.

## Threats → controls (P = preventive, D = detective, R = recovery) → test

| ID | Threat | Controls | Test | Residual |
|---|---|---|---|---|
| T-S1 | spoofed caller | P signed credential, aud/iss, expiry; mTLS (BLOCKED) | `test_security::test_audience_issuer_mismatch_and_forgery` | Med until mTLS |
| T-S2 | spoofed provider | P local socket + ADR-0001 identity (BLOCKED); D re-read verification | `test_provider_invariant_violation_quarantines` | Med |
| T-S3 | stale controller | P epoch fencing, re-validate before call+commit | `test_stale_controller_cannot_commit_after_takeover` | Low |
| T-T1 | tamper audit | P hash chain, HMAC heads; D anchors, readiness | `test_external_anchor_detects_whole_chain_rewrite` | Low (HMAC key custody) |
| T-T2 | tamper journal/state | P checksums/digests; D load verify | `test_mid_file_corruption_blocks` | Low |
| T-T3 | forged rollback record | P record must match authenticated audit, epoch, live state | `test_rollback_records_do_not_cross_epochs` | Low |
| T-R1 | repudiation | P every accepted/rejected authz decision audited with principal & decision id | `test_decisions_are_audited` | Low |
| T-I1 | cross-tenant existence leak | P identical error for missing/foreign guest; authz before lookup | `test_wrong_tenant_and_no_existence_leak` | Low (timing: see T-SC1) |
| T-I2 | secrets in logs | P redaction at every sink; pseudonymous IDs | `test_redaction`, `test_logs_structured_and_pseudonymous` | Low |
| T-D1 | request flood | P admission, rate limit, size limits | `test_controller_overload_bounded_no_duplicate_mutations` | Low |
| T-D2 | retry storm | P retry budget, jittered breaker | `test_retry_budget_prevents_storm` | Low |
| T-D3 | growth starves others | P reserve + tenant caps + reservations | `QuotaTest.test_property_caps_floors_reserve` | Low |
| T-E1 | privilege escalation via fields | P capabilities only from signed claims | `test_reason_and_ids_cannot_escalate` | Low |
| T-E2 | confused deputy | P host-scoped credentials | `test_confused_deputy_controller_chain` | Low |
| T-RP1 | replay of token | P short TTL, jti revocation, audience | `test_revoked_token_and_principal` | Med (no one-time jti) |
| T-RP2 | replay of operation | P idempotency + fingerprint | `test_crash_at_every_phase` | Low |
| T-G1 | guest lies about free pages | P free pages advisory only, bounded; never used as reclaimed memory | `test_model` free-page tests | Low |
| T-G2 | ID reuse | P incarnation check | `test_identifier_reuse_detected` | Low |
| T-SC1 | timing side channel on tenant existence | authz before provider lookup | — | Med (not measured) |
| T-SUP1 | tampered artifact | P RELEASE_DIGESTS + bootstrap integrity; signed provenance (BLOCKED) | `release.py` evidence verify | Med |
| T-ESC1 | hypervisor escape | out of scope; hardening review BLOCKED on provider | — | High (unassessed) |

## Least privilege (C042, C043)
Run as dedicated non-root user; state dir `0700` (bootstrap checks); only provider socket, state dir, lease
dir readable/writable; no outbound network except provider/lease/policy/export endpoints (systemd unit in
`ops/inv32.service` enforces `ProtectSystem=strict`, `PrivateTmp`, `NoNewPrivileges`, `RestrictAddressFamilies`,
`IPAddressDeny=any` + allowlist). No shell execution anywhere in the package (checked by
`release.py sast`). Provider endpoint and module names are configuration-only, never caller-controlled.

## Encryption & keys (C047)
In transit: mTLS for all remote paths (deployment, BLOCKED PKI). At rest: encrypted volume (BLOCKED
deployment). Keys by `secret://` reference; rotation via `Keyring.rotate/retire`; key-service outage → existing
keys until expiry, then FROZEN_WRITE. Certificate expiry alerting: `ops/alerts.json` `Inv32CertExpiringSoon`.
