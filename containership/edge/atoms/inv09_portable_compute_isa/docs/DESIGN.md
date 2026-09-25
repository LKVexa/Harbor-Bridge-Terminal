# INV-09 v4.3.0 — Production validation boundary: design

**Scope.** This document is the M01–M13 design record and the architecture reference for every
other component in the production missing-components checklist. Normative words (MUST, MUST NOT,
SHOULD) are used in the RFC 2119 sense.

## 1. Data flow and trust boundaries

```
 untrusted bytes ──► [TB-1] snapshot (bytes copy) ──► M07 digest ──► M09 cache (MAC'd, epoch-keyed)
                                                                       │ miss
                                                                       ▼
                  M13 governor ─ bounds ─► M01 decoder ─► M02 type validator ─► M03 facts
                                                                       │
             M05/M06/M22 policy bundle (signed, epoch)  ──►  policy evaluation ◄── M17/M18 host contract
             M04 capability manifest (digest-bound)     ──►        │
                                                                   ▼
                                                     M08 Ed25519 attestation
                                                                   │
 caller ──► [TB-2] admit(bytes, attestation) ── verify sig/expiry/bindings ──► M10 AdmissionTicket
                                                                   │
 engine ◄── [TB-3] execute(ticket) ── re-hash snapshot, re-check epoch (M11) ──┘
```

* **TB-1 (module ingress).** Everything before the decoder is attacker-controlled: bytes, the
  capability manifest, trace headers. Nothing from a manifest or header is treated as a fact.
* **TB-2 (attestation ingress).** An attestation is only trusted after Ed25519 verification against a
  pinned key set, expiry check, and equality of *every* verdict-affecting binding with the live config.
* **TB-3 (engine handoff).** The engine receives only `ticket.module_bytes`, an immutable private copy
  whose digest is re-checked at the point of use.
* **Trusted:** the policy bundle once its signature verifies (M22), the host-import contract, the
  signing key (HSM/KMS in production), the Python runtime and this package's code (M45–M47).

## 2. Invariants (security properties)

| ID | Invariant | Enforced by | Tests |
|---|---|---|---|
| I-1 | No module executes without a current, valid attestation for its exact digest | `Gate.admit`, `Gate.execute` | `AdmissionTest.*`, `test_toctou` |
| I-2 | `used_features` is derived only from bytes | `typecheck.validate_module` returns facts; there is no parameter to inject them | `FeatureTest`, `test_binding_manifest` |
| I-3 | Used-but-undeclared, unknown, or out-of-profile features are refused | `Gate._validate_uncached` | `test_binding_manifest`, `test_profile_refusals` |
| I-4 | Every decode/typing defect is a structured refusal with offset + section | `errors.InvalidModule`, `@boundary` | `DecoderTest`, `TypeCheckTest`, fuzz oracle |
| I-5 | Unexpected exceptions never become an accept | `@boundary` → `INTERNAL_ERROR` → outcome `error` | `test_internal_error_is_refusal`, `FaultInjectionTest` |
| I-6 | Resource use is bounded before allocation | `limits.Governor`, `Reader.count` (count ≤ remaining bytes) | `test_vector_bombs_and_limits`, `test_deep_nesting…` |
| I-7 | Configuration only moves forward; stale tickets are refused | epoch check in `activate`/`execute` | `test_stale_config_blocks_execution_and_rollback` |
| I-8 | Cached verdicts are keyed on every input and integrity-protected | `ValidationCache` (key tuple + HMAC) | `CacheTest`, `test_cache_corruption_cannot_admit` |
| I-9 | Deterministic profiles never admit NaN-sensitive code onto an engine without NaN canonicalisation | engine check in gate | `test_nan_canonicalisation_required` |
| I-10 | Unknown host imports are refused | `HostContract.classify` | `HostImportTest` |

## 3. Components (normative requirements)

### M01 Raw binary decoder (`prod/decoder.py`)
MUST: exact magic `\0asm` and version 1; LEB128 u32/s32/s33/s64 within width, with unused high bits
zero/sign-extended; section order 1..9,12,10,11 with customs anywhere; each non-custom section at most
once; every payload consumed exactly; every vector count ≤ its M13 ceiling **and** ≤ remaining bytes;
names strictly UTF-8; limits `min ≤ max ≤ ceiling`; index spaces checked across sections; memory64,
tags, GC value types → `UNSUPPORTED_PROPOSAL`. MUST NOT: allocate proportional to an unchecked count;
recurse. Output: frozen `ParsedModule`. Non-goals: name-section semantics, component binaries (layer 1).

### M02 Type validator (`prod/typecheck.py`)
MUST implement the core-spec validation algorithm with explicit operand and control stacks for the
certified families (MVP, mutable-globals, sign-ext, sat-float-to-int, multi-value, bulk-memory,
reference-types) and refuse all other proposals by opcode prefix. Constant expressions follow
**Wasm 2.0** (only imported immutable `global.get`). `ref.func` requires a declared reference.

### M03 Feature detector
Features are recorded with the byte offset of first evidence. Float use is a separate fact
(`uses_float`), consumed by the NaN-canonicalisation rule (M16).

### M04 Capability binding (`admission.CapabilityManifest`)
A manifest is bound to one module digest. `used ⊆ declared ⊆ profile`; a manifest for another digest,
declaring unregistered features, or hiding a used feature is `BINDING_MISMATCH`.

### M05/M06/M22 Registries (`prod/registry.py`)
One strict, content-addressed bundle carries the pinned spec feature registry, profiles and engines.
Unknown fields, unregistered feature names, non-deterministic features in a deterministic profile, or a
deterministic profile without NaN canonicalisation are refused at load. Distribution is Ed25519-signed
(`attest.sign_bundle` / `open_signed_bundle`).

### M07 Digest — `sha256:` over exact bytes (ADR-0003). ### M08 Attestation — Ed25519 over canonical JSON (ADR-0004).
### M09 Cache — see I-8; only deterministic outcomes cached; accept verdicts re-signed on every hit.
### M10/M11 Admission — `admit` → `AdmissionTicket`; `execute` re-hashes and re-checks epoch.
### M12 Failure schema — `schemas/PK_VALIDATION_FAILURE-1.json`; details sanitised and ≤ 240 chars.
### M13 Governor — `Limits` (revisioned, bound into attestations), step budget, monotonic deadline.

## 4. Concurrency
`Gate` reads `(bundle, contract)` once per request (consistent snapshot); `activate` swaps both under a
lock and bumps the cache epoch. `ValidationCache` is lock-protected (race test: `test_thread_safety`).
`Governor`/`Reader` are per-request and never shared. Validation is pure; no global mutable state.

## 5. Failure modes
| Mode | Behaviour |
|---|---|
| deadline / step budget | `DEADLINE_EXCEEDED` / `LIMIT_EXCEEDED`, outcome `error`/`reject`, not cached; retry safe |
| signer (HSM) unavailable | exception to caller; no verdict, no attestation (`test_signer_failure_is_not_accept`) |
| audit sink failure | exception to caller (fail closed: no unaudited accept) |
| bundle signature/schema invalid | activation refused, previous config stays live |
| cache entry tampered | discarded, module re-validated, `integrity_failures` metric |

## 6. Performance (measured, see `evidence/benchmark.json`)
The pure-Python validator runs at ~1.7 MiB/s: p99 ≈ 0.4 ms at 1 KiB but ≈ 40 ms at 64 KiB and ≈ 2.4 s at
4 MiB. **The README SLO (p99 < 20 ms up to 4 MiB) is not met** — M30 gate FAIL. ADR-0006 records the
remediation (native decoder core behind the same interfaces, with this implementation retained as the
differential oracle).
