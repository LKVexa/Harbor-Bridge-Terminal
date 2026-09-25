# INV-66 threat model (MC-036)

Method: STRIDE per trust boundary, plus abuse cases. Every threat has an ID, controls
(**P**reventive, **D**etective, **R**ecovery) and the tests that exercise it. Residual risk is
rated with a provisional **L/M/H** scale because the organisation's approved method isn't
available here (OPEN_HUMAN). **Review triggers:** any change under `schemas/`, `production/identity.py`,
`rbac.py`, `provenance.py` or `journal.py`, and every production exit gate.

## Assets

A1 the admission decision (what reaches INV-63) · A2 the journal and its anchors ·
A3 the policy document (RBAC, registries, signers) · A4 the anchor signing key · A5 tenant inventory
and audit data (confidentiality) · A6 availability of admission.

## Trust boundaries and entry points

B1 client → API (JWT/mTLS) · B2 operator/admin → API · B3 GitOps checkout → ingestor ·
B4 INV-66 → GAP-13 · B5 INV-66 → INV-63 · B6 INV-66 → journal volume · B7 anchor signer →
journal · B8 audit export → SIEM.

## Actors

malicious tenant · malicious or compromised admin · compromised service identity · compromised
admission replica · registry compromise · signer-key compromise · policy-engine compromise ·
storage compromise · network attacker.

## Security invariants

- **INV-S1** An unadmitted manifest is never forwarded (I1).
- **INV-S2** No admission without a durable journal record (I2).
- **INV-S3** A principal comes only from a verified credential.
- **INV-S4** Cross-tenant data is never disclosed through the inventory, audit or explain APIs without a capability at that scope.
- **INV-S5** Policy changes need N distinct approvers who are not the author.
- **INV-S6** Journal tampering is detectable by anyone holding the anchor public key.

## Threats

| ID | STRIDE / abuse | Threat | Controls | Tests | Residual |
|---|---|---|---|---|---|
| T01 | Tampering | Deploying from an attacker's registry | P: registry allow-list per scope; digest pinning. D: `admit.decision` with `ECP_REGISTRY_NOT_APPROVED` | `test_T01_*`, fuzz | L |
| T02 | Elevation | Developer deploys to production | P: RBAC deny-overrides. D: `admit.refused` + `ecp_rbac_denials_total` | `test_T02_*`, `RbacTest` | L |
| T03 | Tampering / Repudiation | Audit trail rewritten after an incident | P: append-only + flock. D: hash chain, Ed25519 anchors, startup verify, `verify_audit_background`. R: backup/restore | `test_T03_*`, `JournalTest.*`, `test_background_verification_alerts` | M (the anchor key is local until the KMS adapter exists: W-05) |
| T04 | Spoofing | Forged or stolen token, bare username | P: EdDSA only, issuer/kid/aud/exp/nbf/lifetime/jti; optional single use | `test_T04_*`, `IdentityTest.*`, token fuzz | M (no live revocation list: W-02) |
| T05 | Tampering / replay | Signature replayed onto another component or digest | P: signature binds digest **and** name with domain separation | `test_T05_*`, `ProvenanceTest` | L |
| T06 | Elevation | Signer used outside its scope; revoked or expired signer | P: signer scope, `revoked`, `not_after` | `test_T06_*`, `test_revoked_and_expired` | L |
| T07 | Confused deputy | Workload identity acting for another tenant | P: SPIFFE tenant confinement; `.`/`..` segments rejected | `test_T07_*`, `test_spiffe_peer` | L |
| T08 | Elevation | Privilege escalation through delegation | P: `check_delegation` subset rule | `test_T08_*` | L |
| T09 | Tampering / log forging | Injection via names and control characters | P: schema patterns, JSON logs, allow-listed log keys | `test_T09_*` | L |
| T10 | DoS | Parser bombs, huge manifests, deep JSON | P: schema `additionalProperties:false`, component/byte limits, 8 MB body cap, RecursionError → 400 | `test_T10_*`, `test_http_errors_are_typed_envelopes` | L |
| T11 | Tampering | Idempotency key reused to swap the body | P: request digest bound to the key | `test_T11_*` | L |
| T12 | Info disclosure | Tokens or secrets in logs or the journal | P: principal ref only, log allow-list, error detail allow-list | `test_T12_*`, `ErrorRegistryTest` | L |
| T13 | Elevation | A single actor lifts a freeze | P: 2 distinct votes | `test_T13_*` | L |
| T14 | Repudiation / DoS | A freeze silently lost on restart | P: freeze journaled and replayed | `test_T14_*` | L |
| T15 | Elevation | A malicious admin approves their own policy change | P: author ≠ approver, N approvals, CAS | `test_T15_*`, `ConfigTest` | M (both approvers could collude; mitigated by review automation) |
| T16 | Info disclosure | Timing or error oracle on authentication | P: generic message; `cryptography` Ed25519 | `test_T16_*` | L |
| T17 | SSRF / local file read | A config endpoint pointing at `file://` | P: http(s)-only adapter check + schema pattern | `test_T17_*` | L |
| T18 | DoS | Noisy-neighbour tenant | P: per-tenant token bucket + per-tenant in-flight cap | `test_quota_*`, `test_shedder_fairness` | L |
| T19 | Tampering | Stale leader writes after failover (split brain) | P: lease epoch fencing + journal flock | `test_stale_leader_is_fenced`, `test_site_loss_failover_with_fencing` | M (depends on the storage layer's lock semantics: W-04) |
| T20 | Supply chain | Compromised policy engine returns `allow` | P: GAP-13 can only add denials; version pin | `test_policy_version_pin` | L |
| T21 | Supply chain | Registry compromise swaps artifact bytes behind a tag | P: digest pinning is mandatory in prod; optional resolver | `ProvenanceTest` | M (a live registry resolver is OPEN_EXTERNAL) |
| T22 | Supply chain | Signer key compromise | R: revoke in a config generation (N approvals) + `policy_impact` dry run to find affected workloads | `test_policy_impact_dry_run` | M (no transparency log: W-06) |
| T23 | Info disclosure | Cross-tenant read through inventory/audit/explain | P: scope-aware `inventory.read` / `audit.read` / `explain.read`; lattice filter needs a tenant | `test_audit_cursor_pagination_and_filters`, `test_audit_api_contract` | L |
| T24 | Tampering | GitOps webhook replay or forged commit | P: GitOps goes through normal admission + idempotency per commit+path. **Commit signature verification and webhook auth are not built** | `test_gitops_ingestion_goes_through_admission` | H → W-08 |
| T26 | Elevation | A config change lowers its own approval bar (`config_activate: 1`) or rolls back to a weaker generation | P: required approvals = max(active, proposed); a rollback to a weaker generation needs fresh approvals (adversarial review R1) | `test_R1_*` | L |
| T27 | Elevation | A tenant admin removes a deny that an org admin placed on their subtree | P: the creator's authority is journaled; the remover must hold rbac.admin at least as broad (R2) | `test_R2_*` | L |
| T28 | Info disclosure | An idempotency key replayed by another principal returns someone else's decision | P: keys scoped by issuer+subject (R3) | `test_R3_*` | L |
| T25 | DoS | Journal disk full | P: fail closed (`ECP_AUDIT_UNAVAILABLE`), readiness false. R: retention/compaction | `test_journal_failure_admits_nothing_and_degrades` | M |

## Open items (owned remediation, pending owner assignment)

T24 (webhook auth + commit signature verification), live JWKS/OIDC discovery, KMS/HSM anchor key,
transparency log, and a live registry resolver. These are tracked in `release/waivers.json`.
