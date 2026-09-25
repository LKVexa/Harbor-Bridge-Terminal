# Integration contracts (G13-MC-038, EXT-01…05)

## GAP-07 — signing/provenance {#gap-07}
* **Envelope:** `PK_POLICY_SIGNED_BUNDLE/1` (`schemas/`). Signature: Ed25519 over `b"PK_POLICY_BUNDLE/1\0" ‖ canonical payload`.
* **Trust source:** `GAP07_TRUST_SOURCE/1` — object with `trust_store() -> TrustStore`; wire form `PK_POLICY_TRUST_STORE/1` (`fixtures/trust_store.json`): `version`, `fetched_at`, keys with `key_id, algorithm, public_key_b64, issuer, environments, not_before, not_after, purpose, revoked, compromised`.
* **Failure semantics:** exception → `DependencyUnavailable` (activation fails closed, current snapshot kept); trust store older than `max_trust_store_age` → REJECTED.

## GAP-04 — disconnected operation
LKG cache `PK_POLICY_CACHE/1` in `state_dir`; `FileFetcher` for sneakernet/USB/local mirror; staleness modes govern offline behaviour.

## EXT-01 — policy authoring {#ext-01}
Output MUST be canonical `PK_POLICY_BUNDLE/1` with monotonic `generation` per `(issuer, policy_id, environment)`. Approval provenance (author, approver ≠ author for high-impact changes, digest) is recorded by the publisher before signing and carried in `extensions.x-approval`. Validate with `parse_bundle` before publication.

## EXT-02 — enforcement points {#ext-02}
Accept only `schema == "PK_POLICY_VERDICT/1"`; anything other than `effect == "allow"` (including errors, timeouts, unknown schema) is enforced as **deny**. Log `bundle.digest`/`generation`/`trace_id` with the enforcement action. Reference behaviour: `tests/test_integration.EnforcementPoint`.

## EXT-03 — identity and attestation {#ext-03}
Admin/API identity: `PK_POLICY_TOKEN/1` (iss, aud, exp, nbf, iat, jti, sub, kind, roles, env, sites, tenants, mfa, auth_time). Request identity/attestation claims enter only via `TrustedContextProvider.context(subject)` into protected namespaces (`identity.*`, `attestation.*`). Provider outage → `ContextUnavailable` (fail closed).

## EXT-04 — key custody {#ext-04}
Private keys never enter GAP-13. Rotation: publish new key in trust store before first use (overlap), revoke old after last bundle expires. Compromise: set `compromised: true` → all bundles from that key fail verification at next load/restart; operator should quarantine active digests and roll back (RUNBOOKS).

## EXT-05 — topology {#ext-05}
`site`, `workload`, `environment` are protected attributes supplied by the context provider from the authoritative topology source; `Lineage.topology_snapshot` records the snapshot used. Stale/unavailable topology → provider raises `ContextUnavailable`.

## Downstream consumers
PLN-01 intent plane, PLN-06 data plane (`residency` protected), PLN-07 security plane — all consume `PK_POLICY_VERDICT/1` under EXT-02 rules.
