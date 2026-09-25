# INV-12 Language Interoperability — Audit Report

**Audited version:** 4.1.0  
**Remediated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** archive integrity, Python implementation, contract consistency, boundary correctness, hardening, tests, version metadata, and production-readiness gaps.

## Executive result

The 4.1.0 package had a material contract/implementation mismatch: it claimed canonical-ABI copy isolation while `CanonicalValue.value` retained the caller's original mutable object. A producer could mutate a list or record after `lower()` and thereby change the value subsequently observed by the receiver. `lift()` also returned the same object reference. That violated the package's central no-shared-memory/no-alias guarantee.

Version 4.2.0 repairs this reference behavior and hardens the boundary against malformed values, race-prone ownership transfer, invalid strings, unchecked floats, mutable registries, and arbitrary host objects. The package now distinguishes what it actually implements from production components still missing.

## Findings and disposition

| ID | Severity | 4.1.0 finding | 4.2.0 disposition |
|---|---|---|---|
| A-001 | Critical | Mutable `list`/`record` values were stored and returned by reference despite a no-sharing claim. | **Fixed.** Lowering snapshots data-only trees; lifting creates a detached receiver copy. |
| A-002 | High | Ownership transfer used an unguarded public Boolean; concurrent lifts could race and public state could be reset. | **Fixed.** Transfer state is private and lock-guarded; ownership is consumed atomically. |
| A-003 | High | `CanonicalValue(...)` could be constructed directly with values that bypassed `lower()` validation. | **Fixed.** Constructor canonicalizes and validates payloads and owner identity. |
| A-004 | High | `f32` and `f64` values were not type-checked at all; arbitrary objects could cross under a float type name. | **Fixed.** Float types require Python floats; f32 refuses silent narrowing/rounding. |
| A-005 | High | Generic composite values admitted arbitrary Python objects, undermining a data-only ABI boundary. | **Partially fixed.** Arbitrary host objects and cycles are rejected. Full nested schema typing still requires a missing type-AST component. |
| A-006 | Medium | Strings accepted lone Unicode surrogates that cannot be encoded as valid UTF-8. | **Fixed.** Strings and record keys are UTF-8 validated. |
| A-007 | Medium | No canonicalization depth, node, container, or string-size ceilings existed. | **Fixed for reference model.** Bounded defaults added; production limits still need schema/config integration. |
| A-008 | Medium | `LANGUAGE_TYPES` and `RANGES` were mutable module dictionaries and could be changed at runtime. | **Fixed.** Registries are exposed through read-only mapping proxies with frozen value sets. |
| A-009 | Medium | The JavaScript model categorically rejected `u64`, conflating JavaScript `Number` with the language's exact `BigInt` capability. | **Fixed.** JS mapping profile includes exact `s64`/`u64` BigInt semantics. |
| A-010 | Medium | Owner identifiers and target owners were accepted without validation. | **Fixed.** Non-empty UTF-8 owner identifiers with a defined size ceiling are required. |
| A-011 | Medium | The behavioral assessment asserted no sharing only with immutable scalars/strings, so it could not detect aliasing. | **Fixed.** Assessment now mutates a nested source after lowering and verifies receiver isolation. |
| A-012 | Medium | Error classes had no stable machine-readable identifiers. | **Improved.** Stable error-code attributes added; a complete external error-envelope/schema is still missing. |
| A-013 | Low | Version/API exports exposed only the component and contract, making boundary primitives inconvenient to test as an API. | **Fixed.** Canonical types, errors, mapping checks, `lower`, and `lift` are explicitly exported. |
| A-014 | High | Previous changelog stated all 100 requirements passed, but the supplied archive does not include `pk_core`, so that external gate cannot be independently reproduced from this archive alone. | **Documented residual.** Runtime tests are reproducible with stdlib plus the parent framework; full `pk_core` conformance remains an integration validation item. |

## Hardening controls added

1. Data-only canonical tree cloning; no arbitrary object-copy hooks.
2. Cycle detection.
3. Maximum nesting depth (64).
4. Maximum items per container (100,000).
5. Maximum total canonical nodes (200,000).
6. Maximum UTF-8 string/key size (16 MiB).
7. Maximum owner identifier size (256 UTF-8 bytes).
8. Strict integer type/range checks that exclude Python `bool`.
9. Strict bool and string type checks.
10. f32 exact-representability validation.
11. Immutable mapping/range registries.
12. Private canonical payload and ownership state.
13. Lock-guarded exactly-once transfer.
14. Access refusal after ownership has moved.
15. Fail-closed handling for unknown types and languages.
16. Exact built-in data types at the trust boundary, rejecting hostile container/scalar subclasses before user-controlled hooks can run.
17. Expanded behavioral tests for aliasing, Unicode, cycles, host objects, hostile subclasses, f32, JavaScript 64-bit integers, and concurrency.

## Validation performed

- ZIP structure inspected for path traversal/symlink risk before extraction: **PASS**.
- Python AST parse for all `.py` sources: **PASS**.
- `compileall` bytecode compilation: **PASS**.
- `CHECKLIST.json` JSON parse and structure: **PASS** (100/100 unique IDs, ordinals 1–100, ten dimensions × ten checks).
- `MASTER.md` coverage of checklist IDs: **PASS** (all 100 IDs present).
- Version consistency (`VERSION`, `__version__`, tests, README): **PASS at 4.2.0**.
- Boundary hardening unittest subset with an audit-only `pk_core` import stub: **9/9 PASS**.
- Optimized interpreter (`python -O`) runtime checks for isolation, cycle refusal, exactly-once transfer, and empty-string handling: **PASS**.
- Full 100-item `pk_core` conformance gate: **NOT EXECUTED** because the dependency/framework is not present in the supplied archive.

The temporary audit stub used to make imports available during isolated runtime testing is not included in the deliverable.

## Residual technical risk

The implementation remains a Python reference model, not a production WebAssembly Component Model canonical ABI engine. In particular, it lacks a schema/type AST for recursively typed composites, actual canonical memory layout and realloc/post-return mechanics, resource-handle ownership, generated bindings, runtime integration, cross-language fixture components, benchmark evidence, fuzzing, observability emission, provenance enforcement, and a reproducible `pk_core` integration gate. These are enumerated in `MISSING_COMPONENTS.md`.

## Versioning decision

The package is bumped from **4.1.0 to 4.2.0**. The changes are backward-oriented hardening and capability corrections while retaining the existing `lower`, `lift`, `check_mapping`, exception types, `COMPONENT`, and contract interface names. The stricter rejection of malformed/unsafe values is intentional security behavior rather than a wire-contract rename, so a minor bump is appropriate for this package series.

---

# 4.3.0 pass — execution of the missing-components checklist

**Input:** `INV12_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST_v1.0.0.md` (58 components, 3,248 controls,
290 component gates, 12 program gates). **Date:** 2026-09-22. **Result:** see `CHECKLIST_MC_STATUS.md`
(every item annotated) and `MISSING_COMPONENTS.md` (per-component state).

## What was built
`canon/` (21 modules, stdlib only), Rust/Go/JS fixture bindings, a Go→wasip1 guest run in V8, golden corpus,
property/fuzz/differential/malicious-memory/concurrency/leak suites, bench/SLO/DoS harness, CI with a negative
pipeline test, SBOM/artifact policy/release bundle, and eight governance documents under `docs/`.

## Defects found by this pass's own tests and fixed before release
| ID | Defect | Found by | Fix |
|---|---|---|---|
| B-001 | `enum/option/result → variant` despecialization passed the wrong constructor arity | first layout smoke test | constructors corrected |
| B-002 | `CheckedRealloc` keyed live regions by pointer; a zero-size allocation and the next allocation share an address, so accounting reported a false double free | lifecycle review | keyed by allocation id |
| B-003 | overlap check was O(n²) over live regions (quadratic lowering of 100k-element lists) | DoS benchmark design | sorted interval index, O(log n) |
| B-004 | an over-limit 16 MiB+1 string was UTF-8-encoded before refusal (33 MB peak) | DoS suite (`evidence/bench.json`) | refuse on code-point count before encoding |
| B-005 | a list of zero-size elements with count 0xFFFFFFFF would loop 4·10⁹ times in every implementation | corpus/fuzz review | `PK_INTEROP_LIMIT` above 1 000 000 in Python, Rust, Go, JS; golden vector `bad-zero-size-list-bomb` |
| B-006 | own-handle moves were not compensated when a later argument failed to lower | failure-path review | `_TableCodec.undo()`; documented recoverable state |
| B-007 | destructor counter updated outside the table lock | concurrency review | moved under lock |
| B-008 | concurrent calls into one callee instance raced in the (non-thread-safe) guest bump allocator; `CheckedRealloc` caught the resulting overlapping regions and failed the calls closed, and arena reset could interleave with an in-flight allocation | contention stress test under the coverage tracer (intermittent, 1 in ~40 runs) | realloc call + validation + registration + reset serialized per instance; contention test now forces `sys.setswitchinterval(1e-6)` |

## Validation performed (this environment: Linux x86-64, CPython 3.11.15, rustc 1.95.0, go 1.24.7, Node 22.22.2)
- `tools/ci.py`: every engine gate PASS; `pk_core` gates BLOCKED (framework absent) → verdict CONDITIONAL_PASS (`evidence/ci_run.json`).
- 63 unit tests pass in normal and `python -O` mode; line coverage of `canon/` ≥ 90 % (`evidence/coverage.json`).
- Golden corpus: Python, Rust, Go, JS each 50/50 encode byte-exact, 50/50 decode, 17/17 rejections; 16/16 producer→consumer pairs.
- Differential: 1 000 random typed values + 5 000 mutated images across 4 implementations, 0 divergences.
- Fuzz: 20 000 iterations × 3 targets, 0 crashes; regression seeds replayed.
- Real Wasm guest: 8/8 checks (`evidence/wasm_guest.json`).
- Legacy API: `BoundaryHardeningTest` 8/8 PASS with an audit-only `pk_core` import stub that is not shipped.

## Residual risk
Unchanged in kind from 4.2.0 for the items this environment cannot supply: no production Component Model runtime
adapter, no INV-10/11/13/45 artifacts, single platform, no sanitizers, unsigned release, no hosted CI, no `pk_core`
gate, no named owners or peer review. These are recorded as OPEN/BLOCKED/PARTIAL, never as passes.
