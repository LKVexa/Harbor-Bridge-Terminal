# INV-64 security architecture (MC-07, MC-08, MC-14, MC-15, MC-16, MC-17; C023-C024, C039-C050)

## 1. Threat model (C041, C087)

| Threat | Actor | Control | Test |
|---|---|---|---|
| Unauthenticated submission / forged, expired, replayed, wrong-audience, revoked token, `alg=none`, algorithm confusion | external attacker | `auth.Authenticator` fixed verification order; key alg bound by trust config | `AuthnTest` |
| Credential stuffing / auth-failure flooding | external | per-source failure rate limit (not per tenant, so an attacker cannot lock a victim tenant out) | `test_failure_rate_limit_is_per_source` |
| Privilege escalation (vertical: submitter activates; horizontal: tenant A acts on B) | malicious tenant | deny-by-default capabilities, tenant bound to principal, no tenant wildcards | `AuthzTest`, `ServiceTest` |
| Confused deputy via control-plane service | compromised tenant input | cross-tenant only for `service`/`node`/`breakglass` kinds on explicitly named tenants; manifest cannot grant | `AuthzTest.test_cross_tenant` |
| Hostile manifest: parser differential, deep nesting, huge collections, NaN, duplicate keys, invalid UTF-8 | malicious tenant | `manifest.py` ceilings, raw depth scan, duplicate-key refusal | `ParserHardeningTest`, `tools/fuzz.py` |
| Secrets smuggled into config/logs/evidence | careless or malicious user | `secret.inline` refusal, `redaction.redact` on every export, secret scan in CI | `SecretsTest`, `SECRET_SCAN.json` |
| Tampered/unsigned/downgraded artifact or policy | supply-chain attacker | `trust.verify_artifact`, root-signed trust policy, version floor | `TrustTest` |
| Audit tampering or silent loss | insider / disk failure | hash chain + MAC + sealed anchor; bounded buffer; `audit.loss` records; fail-closed critical ops | `AuditTest`, `FAULTS` f07 |
| Cross-tenant data leak via logs/metrics/explain/cache/idempotency keys | curious tenant | tenant-scoped views, no tenant metric labels, tenant-prefixed keys | `TenancyTest`, `STRESS` s5 |
| Resource exhaustion / noisy neighbour | tenant | admission control with per-tenant share, bounded everything | `STRESS` s4, `SemanticsTest` |
| Trust-service outage used to force fail-open | attacker with network position | `OUTAGE_RULES` — cached trust only within window, never new trust | `FAULTS` f08, f10 |
| Side channels (timing on token MAC) | remote | constant-time comparisons (`hmac.compare_digest`) | inspection |

Out of scope for this package (host responsibility): kernel/container escape,
memory isolation between tenants (REG-005), physical attacks.

## 2. Authentication (MC-07)

**Identities** (`auth.IDENTITY_KINDS`): human, workload, node, service,
provider, signer, automation, breakglass. Every boundary in INTERFACES.md §1
names its identity type; anonymous privileged operations do not exist
(`auth.missing`).

**Mechanism:** compact signed token `v1.<header>.<claims>.<sig>`; `HS256` for
service identities with KMS-held shared keys, `EdDSA` (Ed25519) for
asymmetric issuers (requires the `crypto` extra; refused without it). Trust
roots come from a versioned `TrustConfig` supplied by a `TrustSource`
(configuration/KMS/JWKS mirror) — never from a manifest.

**Validation policy:** issuer allowlist; audience = `inv64`; subject, tenant,
kind, jti required; `iat`/`nbf`/`exp` with ±60 s skew; max lifetime 3,600 s
(break-glass 900 s); revocation by token ID or subject; replay cache keyed by
issuer+jti until expiry (full cache ⇒ refuse); optional channel binding
(`cnf` = TLS exporter/peer-certificate digest) — required when
`require_channel_binding` is set, which is the recommended setting for
service-to-service boundaries together with mTLS (`tls_context`).

**Bootstrap and rotation:** a new issuer key is added to `TrustConfig`
alongside the old one (overlap ≥ max token lifetime), then the old key is
removed. No static shared secret ever appears in a manifest (MC-14 refuses it).

**Outage:** keys cached ≤ 300 s verify existing tokens; after that every
request fails `auth.trust_unavailable`.

**Break-glass:** kind `breakglass`, ≤ 15 min tokens, capability `breakglass`
granted to a named role only, every use audited (authn + authz records),
reviewed in the monthly access review (ops/REVIEWS.json). Owner of the
break-glass procedure: `inv64-security-contact` (unassigned).

**Audit:** every authentication success and failure is appended to the audit
ledger with the correlation ID of the request it protects, never the token.

## 3. Authorization (MC-08)

Capabilities: `authz.CAPABILITIES`. Policy `PK_APP_AUTHZ_POLICY/1`
(`schema/authz-policy-v1.schema.json`) maps roles/principals to capabilities
on (tenant, environment, site, resource) with optional identity-kind
conditions. Rules: deny by default; unknown capabilities refused at load; no
tenant wildcards; `*` resource only as a whole selector or trailing `/*`;
separation-of-duties pairs validated at load (recommended:
`release.approve` × `admin.policy`, `admin.trust` × `release.approve`);
policy activation/rollback atomic and audited fail-closed; a policy that fails
to load never replaces the active one. Decisions carry policy version + digest
and are audited (`authz` records) and counted.

**Ambient authority review:** `manifest.py`, `redaction.py`, `errors.py`,
`explain.py`, `oam_profile.py` use no filesystem, network, process, device or
secret authority. `audit.py`, `activation.py` write only under the paths
their owner passes in. `service.py` touches nothing outside its injected
collaborators. `pk_core`'s authority cannot be reviewed — it is not in the
archive (MC-08 blocker). Hosts SHOULD run INV-64 with a read-only root
filesystem except the ledger/store directories, no outbound network except
the audit/telemetry sinks, and no device access.

## 4. Secrets (MC-14) <a id="secrets"></a>

- Prohibited inline: passwords, tokens, API keys, private keys, connection strings with credentials, cloud credentials, signed URLs, JWTs, bearer strings, and any value under a sensitive key name (`redaction.SENSITIVE_KEYS` + suffix rule), including base64/percent-encoded and Unicode-obfuscated forms.
- Approved form: `secretref://<provider>/<key>[@<version>]`. The canonical digest hashes the **reference**, never plaintext. Only the runtime integration (INV-65 providers) resolves references; the parser cannot.
- Messages never echo values that look like credentials (`manifest._show`).
- Exports (logs, audit details, decision records, diagnostics, support bundles) pass `redaction.redact`; `redaction.allowlisted` gives allowlist-based export for support bundles.
- CI: `tools/secret_scan.py` (patterns + entropy) over the tree and built artifacts; reviewed suppressions in `ops/secret_scan_allowlist.json` store only the SHA-256 of the suppressed value.
- No break-glass diagnostic mode exists; none is needed because diagnostics never contain secrets.
- **If a secret is committed or emitted:** (1) rotate it at its provider immediately; (2) record a SEV per ops/INCIDENT_RESPONSE.md; (3) purge from logs/telemetry per TELEMETRY_POLICY retention tooling; (4) rewrite history only with owner approval — the audit ledger is never rewritten (the chain would break); (5) add the pattern to `redaction._PATTERNS` and a regression fixture.

## 5. Artifact trust (MC-15)

Trust policy (`trust.TrustPolicy`, versioned): artifact classes (`wheel`,
`policy`, `schema-bundle`, `overlay-bundle`, `adjacent-contract`, `release`)
→ allowed signers (key IDs pinned in the policy), builders, sources, version
floor/allowlist, denied digests. Accepted envelope: DSSE with an in-toto
Statement v1 (SLSA provenance v1 predicate). Algorithms: Ed25519 (preferred),
HMAC-SHA256 (integrity-only, internal classes). Algorithm agility: a new
algorithm is added as a new signer entry; the old one is removed after all
artifacts are re-signed. Verification order and codes: `trust.py` docstring.
Anti-downgrade: the verifier remembers the highest accepted version per class.
The trust policy itself activates only when signed by an out-of-band root key;
activation and rollback are audited. Offline: previously verified digests
stay valid (cached verification ≤ 24 h); new artifacts are refused while the
provenance service is down. Evidence: `PK_APP_ARTIFACT_VERIFICATION/1` with
policy version and verifier version.

## 6. Isolation (MC-16)

See SPECIFICATION §8 and `tenancy.py`. Shared resources are only providers
explicitly listed in a `SharedResources` contract (fairness: each tenant's
use of a shared provider still counts against its own admission share).
Failover/restore: `TenantRegistry.restore` and `backup_restore --tenant`
refuse records from another tenant.

## 7. Encryption and keys (MC-17)

**Data classification:** manifests and effective configs = *internal* (no
secrets by construction); audit ledger = *confidential* (identities,
topology); decision/telemetry = *internal*; evidence = *internal*; keys and
tokens = *secret* (never persisted by INV-64).

- Transit: `tls_context` — TLS ≥ 1.2 (1.3 preferred), ECDHE+AEAD suites only, no compression/renegotiation, peer certificates required for service boundaries, hostname verification for clients.
- Rest: confidential data (audit ledger, backups) SHOULD be sealed with `crypto_policy.seal` (AES-256-GCM, per-object DEK wrapped by a KEK fetched by key ID from KMS/HSM; tenant bound as AAD) or stored on encrypted volumes. Sealed objects record `kid`, algorithm and nonces only.
- Rotation: `KeyRing.rotate` makes the new key active and the old one decrypt-only; `rewrap` migrates objects; `retire` ends the decrypt window (default 30 days); revoked keys refuse immediately. Emergency compromise: revoke the kid, rotate, rewrap all sealed objects, re-sign artifacts (MC-39), rotate audit MAC/anchor keys and seal a new checkpoint, and record the incident.
- Outages: `OUTAGE_RULES` (identity cached-then-closed, attestation closed, policy last-verified, key closed-for-write, trusted-time closed-if-uncertain, provenance cached verification, audit bounded buffer).
- Metrics: `inv64_crypto_failures_total{kind}` and alert INV64-A10.

Not yet provisioned (blockers): KMS/HSM key provider, service certificates,
managed signer.
