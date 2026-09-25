# INV-07 threat model (STRIDE + replay, supply chain, cross-tenant)

| # | Threat | Vector | Control (module) | Test |
|---|---|---|---|---|
| T1 | Spoofing: unsigned/forged commit deployed | push to approved branch | Ed25519/OpenPGP verify under trust roots, identity + scope + expiry + revocation (`signing`) | `test_git_trust.TestSignatures`, `test_security.TestAdversarial` |
| T2 | Spoofing: key-id confusion | armor claims another key id | key id → key, then verify with *that* key; identity must match committer | `TestSignatures.test_signature_confusion_and_tamper` |
| T3 | Tampering: history rewrite / force push | rewrite main | fast-forward only + freshness generations (`refpolicy`) | `TestRefPolicy`, `TestFreshness` |
| T4 | Tampering: provenance note copied to another commit | notes ref | subject binds commit **and** tree OID (`provenance`) | `TestProvenance.test_note_copied_to_other_commit_fails` |
| T5 | Replay of an old signed commit | ref moved back | generation store, max commit age | `TestFreshness.test_replay_of_old_signed_commit_refused` |
| T6 | Repudiation: rollback not recorded | manual revert | rollback only by signed revert commit; audit chain + seals | `TestEndToEnd.test_full_lifecycle`, `TestAudit` |
| T7 | Info disclosure: secrets in logs/errors/evidence | exception text, URLs | central `redact.scrub` on every sink; credentials via env to git | `TestAdversarial.test_redaction_everywhere`, `TestGitTransport.test_credential_never_in_argv_and_redacted` |
| T8 | DoS: parser bombs, huge blobs, deep nesting | manifests | size/depth/node limits, refuse anchors/aliases | `TestParsers`, `TestFuzz` |
| T9 | DoS: retry storms, overload | dependency outage | retry budget, circuit breaker, bounded fair queue | `TestRetry`, `TestAdmission`, `TestFaultInjection` |
| T10 | Elevation: operator self-approves privileged action | API | two-person rule for `freeze.override`, `trust.rotate`, `rollback.exception`, `restore.run` | `TestAuthz` |
| T11 | Cross-tenant escape | namespace in manifest, path traversal, secret ref | `TenantScope` checks namespaces, cluster kinds, paths, secret prefixes | `TestTenancy` |
| T12 | Split brain | paused leader wakes | lease epoch fencing at the target | `TestLease`, `TestEndToEnd.test_two_controllers_*` |
| T13 | SSRF / DNS rebinding | repo URL, sinks | scheme/host allowlist, private-range refusal after resolution | `TestNetsec`, `TestGitTransport.test_url_policy_rejections` |
| T14 | Supply chain: malicious dependency | pip | zero third-party runtime deps; SBOM; lint gate | `test_tools.TestSBOM`, `TestLint` |
| T15 | Git option injection | ref names like `--upload-pack` | ref regex, `--end-of-options`, OID regex | `TestGitTransport.test_ref_and_oid_injection_rejected` |
| T16 | Clock manipulation to extend a revoked key | time | trusted time source, jump detection, hard revocation mode | `TestTime`, `TestSignatures` |

Residual risks: live-cluster RBAC misconfiguration, KMS compromise, and Git host compromise are outside this archive's reach (BLOCKED items).
