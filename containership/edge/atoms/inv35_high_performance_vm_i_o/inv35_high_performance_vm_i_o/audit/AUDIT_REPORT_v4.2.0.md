# Audit Report - INV-35 High-performance VM I/O v4.2.0

## Scope

The supplied 4.1.0 archive contained eight files: package metadata, `component.py`, `contract.py`, a 100-item checklist, README/changelog, and one `pk_core`-dependent conformance test. This pass audited code, metadata, test behavior, documented claims, and repository completeness, then updated the package to 4.2.0.

## Material defects found in 4.1.0

1. **False-green test gate:** all three conformance tests were skipped when `pk_core` was not importable; unittest still returned `OK (skipped=3)`.
2. **Queue-depth semantic defect:** `QUEUE_DEPTH` was documented as a descriptor bound but `in_flight` incremented once per submitted chain. A guest could therefore reserve as many as `QUEUE_DEPTH * MAX_CHAIN` descriptor entries while the queue still appeared within its bound.
3. **Incomplete untrusted-index validation:** head and `next_index` values were not type/range validated before lookup; Python boolean/integer aliasing could cause `True` to address slot `1`.
4. **Incomplete descriptor-field validation:** negative addresses and boolean values were not explicitly rejected at the trust boundary.
5. **No stable snapshot of the submitted mapping:** the queue walked the caller's live mapping directly.
6. **No synchronization:** concurrent submissions could race on queue-capacity checks and state mutation.
7. **Guest-memory coverage was overly simplistic:** one descriptor had to fit entirely in one registered region even when adjacent registered regions formed continuous guest memory.
8. **Package import unnecessarily required external certification tooling:** `__init__.py` eagerly imported `pk_core`-dependent modules, preventing isolated testing of the datapath model.
9. **Documentation mismatch:** README stated that `MASTER.md` was included, but it was absent.
10. **Readiness overclaim:** the 4.1.0 changelog said all 100 requirements were satisfied even though the supplied archive lacked the certification dependency and most production artifacts/evidence.

## Fixes applied in 4.2.0

- Added standalone `io_model.py` and lazy `pk_core` loading.
- Enforced descriptor-entry queue accounting and exact completion release accounting.
- Added strict fail-closed validation for indices, fields, mapping contents, address ranges, loops, chain length, and queue capacity.
- Added a stable descriptor-map snapshot and frozen descriptor records.
- Added queue locking for capacity/state mutation.
- Added continuous guest-memory coverage across adjacent/overlapping regions.
- Added standalone security/correctness/concurrency tests and repository-integrity tests.
- Added fail-closed `verify.py` plus Windows `VERIFY.cmd`; missing `pk_core` now yields a distinct partial-verification exit code instead of a silent green gate.
- Corrected README/readiness claims and added machine-readable plus human-readable post-update audit artifacts.

## Post-update readiness

`AUDIT_MATRIX.json` classifies the 100 checklist requirements as:

- **Present:** 8
- **Partial:** 23
- **Missing:** 69

There are therefore **92 open checklist requirements**. These are enumerated in `MISSING_COMPONENTS.md`, along with repository-level omissions such as licensing, dependency pinning, CI, static analysis, interface schemas, release evidence, benchmarks, fuzzing, telemetry assets, supply-chain attestations, and ownership metadata.

## Verification result

- `python -m compileall`: **PASS**.
- Normal-mode unittest discovery: **35 tests run; 32 passed and 3 `pk_core` integration tests skipped**.
- Optimized-mode (`python -O`) unittest discovery: **same result**, proving the standalone checks do not disappear under optimization.
- 5,000 randomized hostile descriptor-input smoke iterations completed without an unexpected exception type.
- `python verify.py`: **`VERIFY=PARTIAL` / exit 2** because the supplied archive and execution environment do not include `pk_core`.

The standalone results validate the reference datapath model and repository integrity, but the external 100-item `pk_core` certification flow cannot be executed here. The verifier intentionally distinguishes this from a full pass until the approved pinned `pk_core` is available.
