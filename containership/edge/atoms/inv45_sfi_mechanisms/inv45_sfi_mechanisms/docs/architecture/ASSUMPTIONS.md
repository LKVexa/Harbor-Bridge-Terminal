# Assumptions and unsupported deployments (C005, C008)

Status column: **ENFORCED** (code refuses otherwise), **PREFLIGHT** (detected at start by
`cli preflight` / `engine.preflight`), **EXTERNAL** (prerequisite the operator must guarantee; not checked).

## Assumptions matrix

| Id | Area | Assumption | Status |
|---|---|---|---|
| A-01 | CPU/MMU | Host engine provides linear-memory bounds checks/guard pages for its own memory object. | EXTERNAL (engine) |
| A-02 | Pointer width | Guest address space is 32-bit (wasm32); memory64 rejected. | ENFORCED |
| A-03 | Endianness | Wasm is little-endian by specification; host endianness irrelevant to the verifier. Big-endian hosts are untested. | EXTERNAL |
| A-04 | Runtime / JIT | V8 via Node 20/22/24 with the permission model. JIT output is the engine's; this component does not verify native code. | PREFLIGHT (version, permission model) |
| A-05 | OS | Linux x86-64 tested; macOS/Windows/aarch64 declared-untested. | EXTERNAL |
| A-06 | Container/VM | The verifier process is trusted; guest code never runs in it (guest runs only in the engine subprocess). | ENFORCED (architecture) |
| A-07 | Host page protections | Engine keeps JIT code W^X. | EXTERNAL (R-05) |
| A-08 | Threads / shared memory / atomics | **Not supported** — rejected at parse time. | ENFORCED |
| A-09 | Signals / exceptions | Wasm exception handling rejected; host signals handled by the engine process; a crashed engine process is a failed job, never a partial trust state. | ENFORCED |
| A-10 | Dynamic linking | No module linking; only allowlisted function imports and one imported memory. | ENFORCED |
| A-11 | Runtime code generation | Host `eval`/`Function` disabled in the engine process; guest cannot generate code. | ENFORCED (flag) |
| A-12 | Trust: verifier/rewriter | The rewriter is untrusted for correctness; the verifier is trusted. | ENFORCED (verify after rewrite) |
| A-13 | Trust: loader | `SfiService.load` is the only load path; operators must not expose the engine adapter directly. | EXTERNAL (deployment) |
| A-14 | Trust: policy source | Config generations are written only via `sfi.policy.write`; the base layer is release-reviewed. | ENFORCED |
| A-15 | Trust: `pk_core` | Trusted for checklist evaluation only; never on the enforcement path. | ENFORCED (optional import) |
| A-16 | Trust: fallback tiers | No automatic fallback to weaker isolation; a missing engine is `SFI_DEPENDENCY_UNAVAILABLE`. | ENFORCED |
| A-17 | Network | No runtime network dependency; key/revocation refresh is pushed by the control plane. | ENFORCED (no network code) |
| A-18 | Revocation freshness | Trust material older than `trust_max_age_seconds` grants nothing new. | ENFORCED |
| A-19 | Time sync | Host clock within ±60 s of the control plane (descriptor expiry, token expiry). | EXTERNAL |
| A-20 | Storage: artifacts | Addressed by SHA-256; bytes re-hashed at load. | ENFORCED |
| A-21 | Storage: config/state/audit | Local POSIX filesystem with atomic `rename` and `fsync`; not a network FS without those guarantees. | EXTERNAL |
| A-22 | Storage: temp files | Engine jobs use a private temp dir removed after the job. | ENFORCED |
| A-23 | Verifier cache | In-memory only, keyed by (artifact digest, profile digest); cleared on config change. | ENFORCED |
| A-24 | Control plane: identity | Identity provider key held by reference (`trust.idp_key_ref`). | ENFORCED |
| A-25 | Control plane: rollout | Rollout controller is external (RUNBOOKS.md); the component exposes health and quarantine. | EXTERNAL |
| A-26 | Control plane: attestation | No node attestation in this release. | EXTERNAL / OPEN (C044) |

## Unsupported deployment patterns

Each row has a deterministic failure mode and a test proving it cannot silently enter production.

| Id | Pattern | Deterministic failure | Test |
|---|---|---|---|
| U-01 | Untrusted/raw loader path (bytes without descriptor) | no API exists; wrong bytes → `SFI_DIGEST_MISMATCH` | `ServiceEndToEnd.test_raw_artifact_cannot_be_loaded`, `T02` |
| U-02 | Writable executable pages / runtime codegen in host | engine started with `--disallow-code-generation-from-strings`; permission model probe | `engine.preflight` (permission_model_denies_writes) |
| U-03 | Unverified JIT/rewriter output | verify-after-rewrite; loader re-verifies | `RewriteVerifyTest.test_verifier_independent_of_rewriter` |
| U-04 | Unsupported CPU modes / features (SIMD, threads, memory64…) | `SFI_UNSUPPORTED_FEATURE` | `StructureTest.test_unsupported_features` |
| U-05 | Mutable verified artifacts | digest bound in descriptor, re-hashed at load | `T02_ToctouArtifactSwap` |
| U-06 | Unknown schema/profile versions | `SFI_UNSUPPORTED_VERSION` | `T07.test_unknown_schema_versions_refused` |
| U-07 | Far-edge node without Node ≥ 20 or permission model | preflight `ok: false`; `NodeV8Engine` raises `SFI_DEPENDENCY_UNAVAILABLE` | `engine.preflight` |
| U-08 | Shared memory between tenants without disjoint partitions | operator error; partitions are configured per instance — **not detected automatically** | none (waiver W-04) |
| U-09 | Secrets inline in configuration | `SFI_CONFIG_INVALID` | `T10.test_secret_values_rejected_in_config` |
| U-10 | Network filesystem without atomic rename | not detected | none (EXTERNAL A-21, waiver W-05) |

Startup preflight: `python -m inv45_sfi_mechanisms.production.cli preflight` (exit 3 on failure).
