# INV-26 Threat model (STRIDE + attack trees) — C041, C087

**Status:** DRAFT — security-owner review pending (role unassigned). Every threat below maps to a control and
to at least one executable test; `tests/test_threats.py` asserts the mapping is complete.

## Assets
A1 guest memory (secrets, keys, tokens) · A2 guest RNG state · A3 snapshot metadata/manifest · A4 DEKs/KEKs ·
A5 restore grants and caller credentials · A6 audit trail · A7 configuration/policy.

## Actors
Malicious tenant · compromised guest · malicious/compromised operator · compromised node (worker) ·
supply-chain attacker · network attacker.

## Trust boundaries
`ops/boundaries.json` B01–B12 (API, grant, VMM socket, working files, entropy channel, storage, KMS, metadata,
audit, telemetry, configuration, environment).

## Threats
| ID | STRIDE | Threat | Control(s) | Test |
|---|---|---|---|---|
| T01 | I | Cross-tenant restore leaks guest memory | tenant binding, caller-scope authz, grant binding | test_service.Boundaries.test_cross_tenant_refused_before_side_effects |
| T02 | E | Confused deputy: caller for tenant B names tenant A's snapshot | authorize() on request scope | test_service.Boundaries.test_caller_scope_cannot_be_bypassed_by_request_fields |
| T03 | S | Forged / tampered / alg-confused credential | EdDSA only in production, kid/role/trust-domain | test_security_units.AuthTests.test_tampered_signature_and_alg_confusion |
| T04 | R | Replay of a restore grant to start extra clones | durable one-shot nonce CAS | test_service.AntiReplay.*, test_concurrency.ThreadRaces.test_concurrent_replay_of_one_grant_commits_once |
| T05 | I | Two clones share RNG state | fresh seed + proof per restore; READY only after ack | test_concurrency.ThreadRaces.test_many_distinct_restores_in_parallel, test_adapters.*lying_agent* |
| T06 | T | Snapshot blob tampering / chunk reorder / truncation / transplant | AES-GCM per chunk with index/total/final + context AAD | test_security_units.CryptoTests.* |
| T07 | I | Snapshot exfiltration from storage | envelope encryption, 0600 files, tenant-prefix storage | test_service.HappyPath.test_blob_at_rest_is_ciphertext |
| T08 | T | Device-state confusion (model changed) | SHA-256 device fingerprint refusal | test_service.Boundaries.test_model_mismatch |
| T09 | T | Rollback to a vulnerable/stale snapshot or grant | grant binds manifest digest + generation; rewrap invalidates old grants | test_service.AntiReplay.test_grant_bound_to_node_vm_and_manifest, drills key_rotation |
| T10 | D | Resource exhaustion by one tenant | token bucket, per-tenant slots, quotas before work | test_service.Admission.*, test_service.CaptureSemantics.test_quota_rejects_before_hypervisor_work |
| T11 | T | Malicious/corrupt manifest or hostile request | strict schemas, bounded parser, fuzzing | test_fuzz.*, test_security_units.SchemaTests.* |
| T12 | I | Secret leakage via logs/errors/metrics | public envelope, redaction, no seed/DEK in outputs | test_service.Observability.test_no_secret_material_in_logs_audit_or_responses |
| T13 | E | Operator abuse / break-glass misuse | capability split, bg reason + 15 min cap, fail-closed audit | test_service.OperatorControls.* |
| T14 | R | Audit trail deletion/rewrite by compromised worker | hash chain + HMAC + sealed anchor (external copy required) | test_service.Observability.test_audit_chain_verifies_and_detects_tamper |
| T15 | S | Spoofed node / cloned identity in another site | trust-domain binding of keys; grant audience=node | test_security_units.AuthTests.test_revocation_and_trust_domain_and_role |
| T16 | T | Unsafe config weakening (disable encryption/binding) | LOCKED invariants, overlay rules, fail-closed activation | test_security_units.ConfigTests.* |
| T17 | I | Plaintext remanence in temp files/page cache | tmpfs workdir, wipe of state files, unlink of mapped memory | test_adapters.FirecrackerEndToEnd.test_full_path (work dir empty) |
| T18 | E | Hypervisor escape / side channels / speculative execution | **out of INV-26's control**: host kernel + VMM (jailer, seccomp) + CPU mitigations; INV-26 never co-locates tenants in one VM | none here (assumption A-HV) |
| T19 | S | Supply-chain substitution of the package | SHA256SUMS + DSSE provenance + SBOM; managed signer pending | tools/release.py verify |

## Explicit assumptions (not mitigated here)
A-HV the VMM/KVM isolation boundary holds; A-KMS the KMS enforces encryption-context binding; A-GUEST the guest
agent is part of the trusted guest image; A-TIME node clocks within ±30 s.

## Residual risk
Memory image plaintext exists in host RAM during load (unavoidable for a VMM restore); on-node compromise with
root defeats every control here — mitigated only by host hardening and attestation (C044 PARTIAL).
