# Security: threat model, trust, isolation, secrets, keys (MC-010, 011, 018, 020, 021, 023)

## Trust boundaries
Caller → **[authn: PLN-07 token]** → service → **[authz: capability × scope]** → controls → graph → **[WAL seal]** → disk.
Reporter → **[authn + reporter kind + intent:report]** → evidence store (never authority).
Policy (GAP-13) → called in-process via adapter; unavailable ⇒ deny.

## STRIDE threat model (contract threats + derived)
| # | Threat | Mitigation | Test |
|---|---|---|---|
| T1 | Tenant declares outside its namespace | scope-bound capabilities; cross-tenant/env edges refused | `test_capability_scoping_is_least_privilege`, core tests |
| T2 | Compromised reporter forges actual state | reporter authn, per-tenant report capability, sequence/time ordering, future-skew rejection; reports never change intent | `test_reporter_cannot_declare…`, `DisconnectedSites` |
| T3 | Declaration flood | per-tenant token bucket, node quota, bulkhead shedding | `test_declaration_flood_is_bounded` |
| T4 | Artifact substitution between plan and execution | sha256 digest pin, approved-version allowlist, trusted signer, signature, provenance, revocation | `test_artifact_verification` |
| T5 | Plan replay against newer graph | plan_id bound to graph_version; `verify_release` | `test_release_replay_refused…` |
| T6 | Spoofed actor | actor comes only from authenticated principal; unknown request fields rejected | `test_spoofed_actor_field_is_ignored` |
| T7 | Secret leakage via intent/diagnostics | secret field/value detection, refs only, redacted logs/errors | `SecretsAndArtifacts` |
| T8 | Tampering with persisted state/audit | hash chain + HMAC seal + snapshot MAC; fail-stop | `test_torn_tail…` |
| T9 | Split-brain double writer | lease + fencing token on every WAL record | `test_lease_fencing…` |
| T10 | Parser abuse / malformed input | strict schema, bounded sizes, 3 000-case fuzz, no E9999 allowed | `test_fuzzed_requests…` |
| T11 | Identity or policy outage used to bypass checks | fail closed (E0010 / E0005) | `test_identity_unavailable_fails_closed` |

## Capabilities (least privilege)
`intent:declare, intent:retract, intent:read, intent:plan, intent:report, intent:rollback, intent:transaction, intent:admin`,
each granted on scope `*`, `tenant` or `tenant/environment`. Default deny. Tokens have ≤ 1 h TTL and can be revoked by `jti`.

## Process isolation profile (deployment requirement)
Run as non-root UID, read-only root filesystem, writable `state_dir` only, no outbound network except identity/policy/
telemetry endpoints, seccomp `RuntimeDefault`, all Linux capabilities dropped. (Deployment manifests live with the
platform; this repository states the profile.)

## Keys (MC-021)
`KeyProvider` gives versioned keys with rotate/retire/destroy; tokens and seals carry the key version so rotation is
seamless (`test_key_rotation…`). Key-service outage fails closed. **At-rest encryption is not implemented** — the
standard library has no authenticated cipher; production must supply a KMS-backed provider and encrypted volume
(waiver W-003). Transport TLS terminates at the service host (out of scope of this library).
