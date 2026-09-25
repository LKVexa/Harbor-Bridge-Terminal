# INV-28 Repository Audit Report — v4.2.0

Date: 2026-09-23

## Scope

This audit covers the supplied standalone `inv28_unikernel_implementations` archive. It includes static parsing, implementation review, input-validation hardening, deterministic-selection review, version consistency, source compilation, domain smoke verification, documentation/inventory reconciliation, and a post-change missing-component audit.

## Defects corrected

1. **Identifier normalization was incomplete.** Language and architecture matching was case/whitespace sensitive. Inputs are now normalized before comparison.
2. **Registry encapsulation was weak.** The mutable public toolchain list allowed callers to bypass duplicate checks. Registry storage is now private and exposed as a read-only tuple snapshot.
3. **Duplicate-name detection was case-sensitive.** `Unikraft` and `unikraft` could coexist. Duplicate keys are now rejected case-insensitively.
4. **Malformed register entries were under-validated.** Empty capability sets, empty capability tokens, invalid review clocks, and non-boolean security-contact flags are now rejected.
5. **Selection tie-breaking depended on insertion/name-max behavior.** Equal-maturity matches now use a stable lexical tie-break independent of registration order.
6. **Known limitations were described by the contract but could not be represented in a `Toolchain` entry.** A validated immutable `limitations` field was added.
7. **README inventory was inaccurate.** It claimed `MASTER.md` was present, although it is absent from the supplied archive. The README now reports that accurately and points to the missing-component report.
8. **Version metadata was advanced consistently** from 4.1.0 to 4.2.0 in `VERSION`, `__init__.py`, README, tests, and changelog.

## Verification performed

- `python -m py_compile` over package and test Python files: **PASS**.
- Standalone domain smoke suite using minimal `pk_core` import stubs: **PASS**.
- Verified normalization, malformed-entry refusal, case-insensitive duplicate refusal, production rejection of experimental/no-contact candidates, stale-review rejection, registry immutability, and deterministic equal-maturity selection.

## Verification not possible from this archive alone

The repository's official conformance test imports `pk_core`. The supplied archive does not include `pk_core`, a lockfile, vendored dependency, or install manifest that obtains it. Therefore the full inherited `assess_all()` 100-check execution and the documented `pk_core run/gate/verify` commands cannot be independently executed from this archive alone.

## Post-fix disposition

The implementation is syntactically valid and its self-contained toolchain-selection domain logic is materially hardened. It is **not a self-contained production package** because multiple declared interfaces, schemas, operational artifacts, integration dependencies, and certification evidence are absent. See `MISSING_COMPONENTS.md` for the complete repository-level gap inventory identifiable from the supplied archive.

---

# v4.3.0 post-remediation audit (2026-09-23)

**Input:** `docs/applied/INV28_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (100 items, 70 P0 and 30 P2), applied through the junkyard chop shop.

## Result
- **MC status** (`ops/MC_STATUS.md`): 77 implemented_unreviewed, 15 partial, 5 decision_pending, 3 blocked_external, **0 complete**. The `rtm` validator refuses `complete` without an independent review record.
- **pk_core** is now vendored and runs (W0-W9 and the gate). The result is GO, 100/100: 32 findings are exercised by running the engine, and 68 are derived from contract declarations. These two figures are reported separately and never merged with MC status.
- **Release gate: NO_GO.** The named blockers are: governance (owners unnamed, ADRs, licence, signing), unapproved waivers, missing independent review, and the performance thresholds still PROPOSED. `tests/test_gates.py` checks that GO is reachable once those inputs genuinely exist, and that removing any single one of 18 inputs gives NO_GO.

## Checks run while building (evidence retained)
- The test profile passes under `python` and `python -O` with no skips (`evidence/TEST_RESULTS.json`).
- The fuzz suite also passed 3 extra seeds × 3000 cases.
- Function-body coverage of the runtime modules is 97.0% (`evidence/COVERAGE.json`).
- Mutation testing killed 298 of 299 non-equivalent mutants, 99.7% (`evidence/MUTATION.json`).
- The stdlib lint, SAST, secret scan and dependency checks are clean, and so are ruff 0.15.11 and mypy 1.20.2. The SBOM is in CycloneDX 1.5.
- Bench and soak ran on the build container (`evidence/BENCH_RESULTS.json`, `evidence/SOAK_RESULTS.json`).

## Defects found and fixed in this pass
See `CHANGELOG.md` §4.3.0. There were three performance or concurrency defects (O(n²) commits, a linear certificate scan, and a lock convoy), a decision-id reproducibility bug, a metrics hot-path bug, and one measurement error in the pass's own coverage tool.

## Not verifiable from this archive
- Real GAP-15, INV-27 and GAP-08 deployments; these were exercised at the seams only.
- Execution of the CI matrix on real runners; only Python 3.11 on Linux was run here.
- The CI matrix beyond CPython 3.11 on Linux.
- Asymmetric signing and a KMS.
- Reference-hardware performance.
- An independent review.
