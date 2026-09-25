# INV-44 v4.3.0 Missing-Components Pass — Report

## Scope
Applied `INV44_v4.2.0_Missing_Components_Professional_Checklist.md` (19
components, 1,135 checkboxes, 100 mapped requirements) to the v4.2.0
candidate (`inv44_wasm_hardening_system_v4.2.0.zip`). Work was additive; the
v4.2.0 runtime (`runtime.py`) is unchanged and its original tests still pass.

## Result
- Components: 6 IMPLEMENTED_LOCAL, 9 PARTIAL, 4 BLOCKED, **0 COMPLETE**.
- Requirements: 27 verified / 56 partial / 17 missing (v4.2.0: 11 / 31 / 58).
  No requirement was downgraded; each changed row keeps `previous_status`.
- Tests: 51 (48 run, 3 lane skips with reasons: pk_core x2, PACKAGING), pass
  normally and under `python -O`.
- Release gate: **NO_GO**, exit 3. A falsifier test shows GO is reachable when
  every input is synthetically satisfied, and that each single missing input
  (tests, pk_core gate, approval, service-identity approver, one component) is NO_GO.

## Why nothing is COMPLETE
Every component's definition of done requires something this pass cannot
produce: a named owner/approver, the pk_core framework, the Swivel toolchain,
key custody, or a real environment. The checklist's own rule is that
documentation alone never closes a component.

## Blocked (owner input needed)
1. MASTER.md — original bytes and their source. Not reconstructed.
2. pk_core — the artifact, version and digest to pin.
3. Licence — outbound terms (pyproject says LicenseRef-Proprietary-Pending).
8. Swivel/runtime — pinned toolchain, real compiles, Spectre evidence.

## Defects found by this pass's own checks
See CHANGELOG 4.3.0 "Fixed during this pass": unaudited live instance on
audit-sink failure; duplicate-name race window; verifier accepting 23.3% of
V8-invalid mutants (now 0.03%); shadowed variable breaking code-section parsing.

## Measured, not certified
`evidence/PERF_RESULTS.json` and `evidence/DIFFERENTIAL_V8.json` are
labelled MEASURED; no thresholds are approved.

---

# INV-44 v4.2.0 Audit / Fix / Hardening Report

## Scope

The supplied `inv44_wasm_hardening_system` archive was parsed as an isolated
repository. Source archive SHA-256: `2f886741b2fe01f0eff847afcd49d98090f74d893dcc9856cbfb66fbc37a71e7`. The pass covered archive safety, repository structure, Python
syntax, version consistency, checklist structure, the runtime enforcement
model, unit tests, optimizer behavior, and a post-update completeness audit.

The archive did **not** contain `pk_core`, so the external estate-level
`pk_core run/gate/verify` path cannot be executed from this package alone.
Version 4.2.0 therefore separates locally verified evidence from external gate
claims instead of treating a skipped dependency as a successful certification.

## Material defects found in 4.1.0

1. **Factory-gate bypass:** `Instance(...)` could be constructed directly,
   bypassing `Engine.check()` and output verification.
2. **Unbounded zero-cost execution:** `step(0)` was accepted, allowing an
   unlimited number of execution steps without consuming fuel.
3. **Mutable enforcement state:** callers could directly rewrite `fuel`,
   `pages`, `consumed`, `trapped`, and engine configuration fields.
4. **Type-coercion ambiguity:** Boolean values were accepted as integers
   (`True == 1`) for security/resource accounting fields.
5. **No concurrency protection:** simultaneous `step()` / `grow()` calls could
   race on mutable accounting state.
6. **Fixed global memory ceiling:** the implementation could not express the
   contract's environment-specific ceiling requirement.
7. **Identifier/control-character injection:** module/engine labels were not
   validated before appearing in exceptions/diagnostics.
8. **Evidence-to-checklist mismatch:** several custom findings were written to
   checklist indices whose requirements they did not actually prove.
9. **False package claim:** README stated that the master prompt/workflow source
   artifact was bundled verbatim, but that file was absent from the archive.
10. **All-or-nothing test skip:** because `pk_core` was absent, the 4.1.0 test
    class skipped even simple version/security checks that did not need it.
11. **Self-certification bias:** the old conformance test required every
    finding to be passing, which can hide genuine repository-local completeness
    gaps when a framework emits generic/default findings.

## Changes in 4.2.0

- Added standalone `runtime.py` with fail-closed validation and no `pk_core`
  dependency.
- Factory-gated `Instance` construction and re-checks hardening at construction.
- Frozen engine/instance public state; internal accounting mutates only under a
  private lock.
- Strict integer validation rejects Boolean/non-integer resource values.
- `step()` now requires strictly positive fuel cost.
- Added immutable per-engine memory ceilings.
- Added control-character and length validation for diagnostic identifiers.
- Added local concurrency/race test for fuel accounting.
- Added adversarial tests for missing hardening features, unverified output,
  direct construction, zero/negative/Boolean cost bypasses, memory ceilings,
  immutable state, and identifier injection.
- Re-aligned custom checklist evidence with requirements it actually supports.
- Split local security tests from optional external `pk_core` conformance tests.
- Removed the test that forced every external finding to appear passing.
- Added a 100-item evidence matrix and explicit missing-components report.
- Added a repeatable stdlib-only repository audit script.
- Added a SHA-256 file manifest and exact shipped-file-set verification.
- Made package initialization lazy so the standalone runtime remains importable/testable without `pk_core`.


## Verification executed after the update

- `python tests/test_component.py` — PASS: 13 tests discovered, 11 executed successfully, 2 skipped because `pk_core` is not supplied.
- `python -O tests/test_component.py` — PASS with the same 11/2 result, confirming the local checks do not depend on optimizer-stripped `assert` statements.
- `pytest -q tests` — PASS: 11 passed, 2 skipped, 12 subtests passed.
- `python -m compileall -q .` — PASS.
- `python tools/audit_repository.py` — PASS; validates version consistency, checklist cardinality/uniqueness, post-audit matrix coverage, checksum/file-set integrity, absence of production bare asserts, and the local test suite.
- Standalone package/runtime import without `pk_core` — PASS.
- `CHECKLIST.json` and `POST_AUDIT_MATRIX.json` JSON validation — PASS.

## Post-update completeness result

See `POST_AUDIT_MATRIX.json` for all 100 checklist entries and
`MISSING_COMPONENTS.md` for the complete human-readable gap inventory.

The current local evidence classification is:

- **11 verified**
- **31 partial**
- **58 missing**

This count is intentionally conservative: a requirement is not marked verified
unless the supplied repository contains direct documentation, implementation,
test, or dedicated artifact evidence for it.
