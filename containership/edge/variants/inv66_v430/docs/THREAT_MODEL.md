# INV-66 threat model (MC-036) and cryptography/key management (MC-027, MC-034)

Document ID `INV66-TM` · v1.0.0 · 2026-09-22 · method: STRIDE per trust boundary + abuse cases · review: every release touching auth/provenance/store, and quarterly.

## Assets
Admission integrity (no unadmitted manifest reaches INV-63); audit history integrity; policy/config integrity; tenant isolation; availability of admission.

## STRIDE by boundary

| # | Threat | Boundary | Mitigation (code) | Test | Residual |
|---|---|---|---|---|---|
| T1 | **Spoofing** caller identity (v4.2 trusted a user string) | Z1→Z2 | JWS verification: issuer allow-list, alg allow-list per issuer, audience, lifetime cap, `jti` single-use (`identity.py`) | `test_security.AuthnTest` | IdP compromise (out of scope; rotate issuer keys) |
| T2 | Token replay | Z1→Z2 | replay cache; optional mTLS `cnf` binding | `test_replay_and_cert_binding` | replay across instances with separate caches inside token lifetime → keep lifetimes ≤ 5 min, bind to certs |
| T3 | Algorithm confusion / `alg:none` | Z1→Z2 | per-issuer alg list; `none` never accepted | `test_rejections` | — |
| T4 | **Tampering**: attacker registry / signer spoof | manifest | digest-pinned images, exact registry match, Ed25519 over domain-separated `{image,digest}`, attestation requirements (`provenance.py`) | `test_supply_chain_rejections…`, `test_signature_replay_onto_other_digest`, `test_registry_confusion` | compromised signer key → revoke via config (`not_after`), GAP-07 transparency adapter |
| T5 | Audit rewrite after incident (contract threat) | Z2 store | hash chain + epoch + HMAC anchors to external WORM (`store.py`) | `test_anchor_detects_full_chain_rewrite` | attacker holding anchor key *and* WORM credentials |
| T6 | **Repudiation** of admin actions | admin API | every config/freeze/lifecycle/export journalled with authenticated principal | `test_config_activation…`, `test_explain_inventory_audit_export` | — |
| T7 | **Information disclosure** across tenants | read APIs | scope-checked inventory/audit/explain; logs redact tokens/secret keys | `test_tenant_isolation`, `test_logs_are_structured_and_redacted` | `/metrics` label values (tenant ids) — bind to ops network |
| T8 | **DoS**: parser bombs, huge manifests, floods | Z1→Z2 | size limits, nesting probe, schema, bulkhead, quotas, bounded caches | `test_parser_bombs_and_non_json`, `test_overload_sheds…`, bench overload | volumetric attacks → upstream rate limiting |
| T9 | **Elevation**: developer deploys to prod (contract threat) | RBAC | scoped capabilities, explicit deny wins, expiry, prod two-person config rule | `test_rbac_scope_and_explicit_deny`, `RbacTest` | mis-configured bindings → quarterly access review (`tools/review.py`) |
| T10 | Confused deputy via GitOps | GitOps | GitOps uses its own service principal through the normal path; path traversal blocked | `test_gitops_changeset_ingestion` | compromised Git host → require signed commits upstream |
| T11 | Stale/duplicate leader (split brain) | HA | lease + fencing epoch checked on every append under `flock` | `test_ha.*` (incl. 4-process race) | shared-FS `flock` semantics must be validated on the chosen storage (W-006) |
| T12 | Dependency compromise (policy engine lies) | Z2→Z3 | mTLS, pinned policy bundle version echoed back, fail closed | `test_http_policy_engine…` | malicious-but-pinned bundle → GAP-13 governance |
| T13 | Supply chain of INV-66 itself | build | pinned constraints, SBOM, provenance attestation in release job, license gate | `tools/sbom.py`, CI release job | CI not yet executed on hosted runners (W-010) |

## Keys and secrets

| Key | Purpose | Holder | Rotation |
|---|---|---|---|
| Anchor/snapshot MAC key (32 B) | HMAC over anchors, snapshots, exports | INV-66 via `secrets.anchor_key` (`env://`/`file://`, 0600) | Rotate by (1) anchor with old key, (2) switch key, (3) anchor again; keep old key in the verifier set until old anchors age out. Multi-key verification is a tracked gap (W-007). |
| Identity issuer keys | verify tokens | public keys (EdDSA) or shared secrets (HS256) via config `identity.issuers[*].keys` by `kid` | add new `kid`, move IdP to it, remove old `kid` after max token lifetime |
| Signer public keys | verify artifact signatures | config `signers[]` (public only; INV-66 never holds signing keys) | add new key, set `not_after` on old |
| TLS server/client certs | transport + mTLS to deps | files referenced by CLI flags | per org PKI; restart to reload |

**At-rest encryption:** the journal contains manifests and principals (no secrets). It must be stored on an encrypted volume (LUKS / cloud KMS-backed disk). Application-level journal encryption is not implemented (W-007).
