# INV-45 threat model (C041, C050, C087)

**Status:** DRAFT for security review — residual risks below require approval by the security owner
(`OWNERSHIP.md`, UNASSIGNED). Re-run this model when the execution technology, loader, engine, supported
CPU or any trust boundary changes (`docs/operations/LIFECYCLE_POLICIES.md` review triggers).

## Assets

Tenant memory contents · host process integrity · sealing keys / IdP key · trust roots · config generations ·
quarantine and anti-rollback state · audit log · verifier correctness.

## Trust boundaries and data flow

```
submitter/CI --(bytes + Ed25519 statement + token)--> [B1 submit: authn, authz, admission,
   quarantine, signature, floor, rewrite, VERIFY, seal] --(rewritten bytes + HMAC descriptor)-->
orchestrator --(bytes + descriptor + token)--> [B2 trusted loader: MAC, authz@digest, replay,
   digest, profile/config binding, quarantine, re-verify, floor] --handle-->
[B3 execute] --JSON job--> node --permission (fresh process, empty env) --> V8 instance(s)
operators --token(s)--> [B4 quarantine / B5 config]      service --> audit log, metrics, logs
```

Privileged components: verifier, loader, key material, config writer. Untrusted: artifact bytes, guest code,
submitter-supplied metadata.

## Threats

Severity: C critical · H high · M medium · L low. "Tests" are class names in `tests/security/test_threats.py`
unless noted; the RTM checker requires every C/H threat to map to at least one existing test.

| Id | Threat (STRIDE) | Sev | Preconditions | Mitigation | Residual risk | Tests |
|---|---|---|---|---|---|---|
| T01 | Memory escape through an unmasked access (E) | C | malicious guest | rewrite + independent verifier; loader re-verifies | engine bug below Wasm level (R-04) | `T01_MemoryEscapeViaUnmaskedAccess`, `EngineEndToEnd`, `RewriteVerifyTest` |
| T02 | TOCTOU: bytes swapped between verify and load (T) | C | write access to artifact store | digest sealed and re-hashed at load | none known | `T02_ToctouArtifactSwap` |
| T03 | Descriptor forgery / replay / expiry abuse (S,T) | C | stolen descriptor | HMAC, strict field typing, one-time nonce, expiry, key revocation | sealing-key compromise → rotate + revoke | `T03_DescriptorForgeryAndReplay` |
| T04 | Cross-tenant confused deputy (E) | C | tenant credential | tenant-bound principals, digest-scoped grants, capability per operation | none known | `T04_CrossTenantConfusedDeputy` |
| T05 | Identity spoofing (S) | H | none | HMAC identity tokens, expiry, issuer check | IdP key compromise | `T05_Spoofing` |
| T06 | Supply-chain: unsigned/modified/revoked artifact (T) | H | CI or registry compromise | Ed25519 statement bound to digest+workload+version, pinned roots, revocation | signer key compromise | `T06_SupplyChainArtifactSignature` |
| T07 | Rollback / downgrade (T) | H | old signed artifact | anti-rollback floors, exact schema ids | floor store tampering (host compromise) | `T07_RollbackAndDowngrade` |
| T08 | Policy bypass via config change (E) | H | policy-write credential | descriptors bound to config digest; base-only weakening switches; capability | insider with base-layer rights | `T08_PolicyBypassViaConfigChange` |
| T09 | Resource exhaustion / DoS (D) | H | submitter | pre-parse size limits, counts, deadline, admission, quadratic-path removal | CPU-bound verify under max limits (~0.6 s/70k instr) | `T09_ResourceExhaustion`, `LimitsTest`, fuzz |
| T10 | Secret / tenant data leakage via errors, logs, metrics (I) | H | log reader | allowlisted details, redaction, secret refs | new fields added without allowlist review | `T10_SecretAndTenantLeakage` |
| T11 | Stale trust material while partitioned (S) | H | control-plane partition | freshness window, `SFI_TRUST_STALE` | window length (≤ 24 h bound) | `T11_StaleTrustMaterial`, `FM06` |
| T12 | Quarantine bypass / self-release (E) | H | tenant credential | capability, dual human authorization for global | two colluding operators | `T12_QuarantineBypass` |
| T13 | Audit tampering / repudiation (R) | H | host file access | hash chain, external checkpoint, denial events | root on the host can rewrite + re-chain unless checkpoints are exported | `T13_AuditTampering`, `AuditTest` |
| T14 | Parser differential verifier vs engine (E) | C | crafted binary | strict profile; differential fuzz vs V8 `WebAssembly.validate` | V8 accepting less than us is safe; the reverse is tested | `ParserFuzz`, `test_accepted_modules_are_engine_valid` |
| T15 | Verifier/rewriter confusion (rewriter bug produces unsafe code) (E) | C | rewriter defect | rewriter untrusted; verifier independent; tamper tests | verifier defect (fuzz + review) | `RewriteVerifyTest.test_verifier_independent_of_rewriter` |
| T16 | Host-call abuse / ambient authority (E) | H | malicious guest | import allowlist, runner provides only allowlisted host functions, permission model, empty env | Node permission model does not restrict network sockets (runner exposes none to guest) | `test_hostcall_not_allowlisted_is_absent` |
| T17 | Runaway guest / infinite loop (D) | M | malicious guest | per-job timeout, process kill, circuit breaker | — | `test_runaway_execution_is_killed` |
| T18 | Side channels: shared cache / branch predictor / Spectre across co-resident tenants (I) | H | co-residency | **not mitigated by SFI masking** (masking is architectural, not speculative); per-process isolation per job reduces but does not remove it | **ACCEPTED-PENDING** (waiver W-02): Spectre-class leakage across partitions in one engine process is out of scope; tenants requiring it must run in separate processes/hosts (INV-39/INV-30) | none (documented) |
| T19 | Timing / telemetry leakage (I) | M | metrics reader | bounded labels, no tenant data in metric values, per-tenant latency only in authorized benchmarks | coarse timing visible to operators | `TelemetryTest` |
| T20 | Compromised adjacent component (engine, pk_core) (E) | H | supply chain | engine pinned major + preflight; pk_core off the enforcement path | engine CVEs (LIFECYCLE_POLICIES.md SLA) | `EnginePreflightTest` |
| T21 | Insider misuse of operator capabilities (E) | M | operator | least privilege, audit of every privileged action, dual auth for global actions | single-operator tenant-scope actions | `T12`, audit tests |

## Residual-risk register (needs approval)

R-01 overhead SLO miss (PERFORMANCE.md) · R-03/R-04/R-05 engine-delegated guarantees (ADR-0001) ·
T18 speculative side channels · T13 host-root audit rewrite without exported checkpoints ·
T16 network syscalls not blocked by the Node permission model. Each is in `docs/WAIVERS.md` with an expiry.
