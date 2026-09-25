# INV-02 container substrate - Audit and hardening report

**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** supplied `inv02_container_substrate` archive only

## Executive result

The package was parsed, hardened, version-bumped, and validated as an in-memory image identity/integrity reference model. The pass fixes policy-bypass, validation, bounded-resource, malformed-manifest, concurrency, quarantine, packaging-import, and test-coverage defects. It does **not** convert the package into a full OCI registry/container runtime; those residual production components are explicitly inventoried in `MISSING_COMPONENTS.md`.

## Findings fixed in v4.2.0

| ID | Severity | Pre-fix finding | Remediation |
|---|---|---|---|
| A-01 | High | Mutable-tag protection depended on exact `env == "production"`; aliases/case such as `prod` or `PRODUCTION` could bypass the rule. | Normalize/validate environment names and protect both `prod` and `production` by default. |
| A-02 | High | Digest references were syntactically checked but could resolve to content not present in the registry. | Require the resolved manifest digest to exist before successful resolution. |
| A-03 | High | Manifest parsing trusted JSON shape and could leak `KeyError`, `TypeError`, or other implementation exceptions. | Add strict UTF-8/JSON/schema/layer descriptor validation and normalized `IntegrityError` failures. |
| A-04 | High | Layer, image, manifest, reference, resolution-history, and provenance growth were unbounded. | Add configurable positive resource ceilings and bounded histories. |
| A-05 | High | Compound operations over blobs/tags/history were not synchronized. | Add an `RLock` around compound mutation/read/verification paths and concurrency tests. |
| A-06 | Medium | Manifest format carried only a list of digests with no explicit schema/media type or layer sizes. | Emit deterministic v1 manifests with schema/media type and size descriptors; retain v4.1 legacy read support. |
| A-07 | Medium | Reference parsing used substring logic and did not robustly model registry ports/tag separators or reject ambiguous forms. | Add a dedicated parser for tag, named-digest, and bare-digest references. |
| A-08 | Medium | No quarantine primitive existed in the reference model. | Add manifest/layer quarantine and explicit release; resolution/pull fail closed while quarantined. |
| A-09 | Medium | Provenance was limited to raw resolution tuples and did not capture tag movement. | Add bounded `ProvenanceRecord` entries with sequence and previous manifest digest. |
| A-10 | Medium | All supplied tests depended on `pk_core` and therefore all tests skipped in a partial checkout. | Add a self-contained stdlib registry test suite that executes without `pk_core`. |
| A-11 | Medium | Importing the package eagerly imported `pk_core`-dependent modules, preventing use/testing of the standalone model. | Make conformance/contract exports lazy; stdlib registry exports import normally. |
| A-12 | Low | README claimed `MASTER.md` was bundled, but the file is absent. | Correct README and track `MASTER.md` as a missing artifact. |
| A-13 | Low | Performance evidence inferred manifests by checking whether stored bytes started with `{`, which is unsafe for arbitrary layer content. | Use registry-maintained manifest identity and explicit statistics instead. |

## Compatibility notes

- v4.2.0 writes a new deterministic private manifest shape but can still read v4.1.0 manifests of the form `{"layers": ["sha256:..."]}`.
- Public `Registry.blobs` and `Registry.tags` remain mutable for compatibility with the original fixture. That is intentionally **not** presented as production-safe storage; replacing them with a durable encapsulated store is a missing production component.
- `pk_core` conformance integration remains API-compatible through the `COMPONENT` lazy export when `pk_core` is available.

## Validation performed

Final isolated validation: **16 standalone tests passed in normal mode and 16 passed under `python -O`; 3 `pk_core`-dependent conformance tests were skipped in each mode because that dependency is absent.**

- Python bytecode compilation of package modules.
- `unittest` discovery over both supplied and new tests.
- Standalone import of the package without `pk_core`.
- Production mutable-tag rejection across normalized environment variants.
- Known/unknown digest resolution behavior.
- Shared-layer de-duplication.
- Tag-movement immutability for digest-pinned content.
- Corrupted layer rejection and repair-on-repush behavior.
- Malformed manifest and descriptor rejection.
- v4.1.0 legacy manifest read compatibility.
- Configured resource ceilings and bounded history.
- Manifest/layer quarantine behavior.
- Concurrent push/resolve/pull consistency.

## Validation limitation

`pk_core` is not present in the supplied archive or current isolated checkout. Consequently, the three estate-wide conformance tests are skipped and **must not be interpreted as passing**. Full 100-item conformance certification requires the complete estate checkout (or a valid `PK_CORE_PATH`) and rerunning `tests/test_component.py` plus the estate gate/evidence commands.

## Residual risk

The implementation remains an in-process reference model. It lacks durable storage, OCI distribution/runtime integration, Linux isolation/resource enforcement, registry authentication/TLS, signature/provenance verification, security profiles, distributed coordination, durable audit, production telemetry, and integration/fault/security certification. See `MISSING_COMPONENTS.md` for the complete inventory.

---

# v5.0.0 — checklist execution pass (2026-09-22)

**Input:** v4.2.0 hardened archive + `inv02_container_substrate_v4.2.0_PROFESSIONAL_COMPONENT_CHECKLIST.md` (78 components, 3,736 checklist items).
**Output:** v5.0.0. Backwards compatible with v4.2.0 (`registry.Registry`, `pk_core` adapter unchanged).

## Result by component (source: `COMPONENT_STATUS.json`)

| Status | Count | Meaning |
|---|---|---|
| implemented | 52 | code + automated tests passing locally |
| implemented+runtime-verified | 7 | also verified inside a real `runc` container (MC05, MC07, MC22, MC23, MC26, MC28, MC59) |
| partial | 11 | core done; named sub-capabilities open (MC04, MC08, MC10, MC21, MC24, MC35, MC53, MC58, MC60, MC65, MC66) |
| implemented-spec | 2 | correct spec emitted; enforcement not exercised on this host (MC25 MAC, MC33 sandboxed runtimes) |
| documented | 3 | operations artefacts needing live validation (MC50, MC51, MC56) |
| owner-action | 3 | licence (MC71), named owners (MC73), SLA/EOL approval (MC78) |

## Validation performed

- `compileall` clean; 108 tests in normal and `python -O` modes: **104 passed, 0 failed, 4 skipped** in each (`evidence/test-results.json`).
- Skips (not passes): 3 `pk_core` conformance tests (dependency absent); 1 rootless user-namespace container (host forbids `MS_PRIVATE` remount inside a user namespace).
- Real-runtime integration: runc 1.3.5 / kernel 6.18.44 / x86_64 / cgroup v1 — container saw PID 1, `mount(2)` denied, `unshare(CLONE_NEWUSER)` denied, rootfs read-only, secret delivered as a mounted file.
- Ed25519 checked against RFC 8032 test vectors 1 and 2; malleable (S ≥ q) signatures rejected.
- Distribution client tested over real HTTP against a local fake registry: bearer/basic auth, wrong manifest, corrupt blob, 5xx retry, truncated-transfer resume via Range, digest-only mirrors, offline mode.
- Adversarial layers refused: absolute paths, `..`, write-through-symlink, hardlink escape, device nodes, decompression bomb, entry-count bomb.
- Seeded fuzzing of the manifest/config/reference parsers, layer unpack and the legacy registry (also run at 4,000 iterations); thread and multi-process races on CAS tags; fault injection (rename failure, fsync failure, corrupt metadata, lock timeout).
- `tools/release_evidence.py` verdict **PASS** (tests in both modes, governance files present, versions consistent, no expired waivers).

## Defects found and fixed during the pass

| ID | Finding | Fix |
|---|---|---|
| V5-01 | Layer path cleaning with `lstrip("./")` would strip the leading dot from hidden files (`.bashrc` → `bashrc`) | strip only literal `./` prefixes |
| V5-02 | Registry `Authorization` header would follow redirects to blob CDNs | send it as an unredirected header |
| V5-03 | Basic-auth branch could not authenticate | store full header values per (host, repo) |
| V5-04 | Seccomp allow-listed `clone`/`clone3` without restricting namespace flags | `clone` limited by `SCMP_CMP_MASKED_EQ` on `CLONE_NEW*`; `clone3` returns `ENOSYS` so libc falls back |
| V5-05 | Capability grants (`cap:SYS_ADMIN`) were not normalised to `CAP_*` | normalise before comparing |
| V5-06 | Device-rule template emitted `"minor": null` | omit absent fields |
| V5-07 | Hard-coded `RLIMIT_NOFILE` 65536 fails on hosts with lower hard limits | `ContainerConfig.nofile` |
| V5-08 | Legacy test asserted a hard-coded version | read `VERSION` |

## Residual risk

Single-host store authority (multi-node lease service open); no overlayfs snapshotter; zstd layers refused; no CNI integration; cgroup v2, userns, MAC profiles, crun/runsc/kata and real remote registries not exercised on this host; Ed25519 is not constant-time (verification only — sign in an HSM/KMS); `pk_core` estate conformance still unrun. No checklist box is ticked: independent verification and the DoD gates remain.
