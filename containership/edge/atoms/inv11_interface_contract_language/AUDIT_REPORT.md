# INV-11 Interface Contract Language — Audit Report

**Audited release:** 4.1.0  
**Hardened release:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** the supplied `inv11_interface_contract_language` archive only.

## Executive summary

The supplied archive was structurally valid and contained a focused reference
implementation, a 100-item checklist, the matching master prompt/workflow
corpus, tests, contract metadata, and release notes. The audit found two
material hardening issues in executable behavior: ambiguous duplicate function
names could be silently collapsed during structural indexing, and the direct
conformance test command returned success when `pk_core` was absent because all
conformance tests were skipped. Release 4.2.0 fixes both and separates the
pure compatibility model from the external estate runtime so it can be tested
independently.

The archive is still a **reference compatibility model**, not a complete WIT
front end or production interface-definition toolchain. The principal missing
implementation components are enumerated in `MISSING_COMPONENTS.md`.

## Package inventory parsed

- `component.py` — `pk_core` component adapter and behavioral evidence hooks.
- `contract.py` — production contract definition.
- `interface_model.py` — new dependency-free structural compatibility model.
- `metadata.py` — new dependency-free element identity metadata.
- `CHECKLIST.json` — 100 requirements across 10 dimensions.
- `MASTER.md` — per-item master prompt/workflow corpus.
- `tests/test_model.py` — new standalone model unit tests.
- `tests/test_component.py` — estate conformance tests with fail-closed direct preflight.
- `README.md`, `CHANGELOG.md`, `VERSION` — operator/release metadata.
- `MANIFEST.sha256` — package integrity manifest generated for the hardened tree.

## Audit findings and disposition

### F-01 — False-green conformance command when `pk_core` is absent — High — Fixed

Previously, every conformance test was decorated with `skipIf(pk_core is None)`.
Executing the documented test file in an isolated copy therefore exited 0 with
all tests skipped. That result could be mistaken for successful certification.

**Fix:** direct execution now performs a dependency preflight and exits 2 with
an actionable message when `pk_core` cannot be imported. Version metadata is
also tested independently of the estate dependency.

### F-02 — Duplicate function names silently collapse during indexing — High — Fixed

`Interface.functions` was a `frozenset`, while `by_name()` constructed a dict by
function name. Two distinct `Func` objects with the same name but different
signatures were legal inputs, and one entry would overwrite the other during
indexing. This makes an invalid interface definition ambiguous.

**Fix:** `Interface` now validates that function names are unique before building
the name index. Duplicate names fail closed with `ValueError`.

### F-03 — Malformed structural values accepted too far into comparison — Medium — Fixed

The original dataclasses accepted empty identifiers, malformed parameter tuples,
duplicate parameter names, non-`Func` function values, and non-normalized
containers.

**Fix:** 4.2.0 validates and normalizes dependency-free model inputs before any
compatibility or link decision is made.

### F-04 — Mixed breaking/additive diffs lost additive diagnostics — Medium — Fixed

When any breaking change had already been found, newly added functions were not
reported in the reasons list. The classification was still breaking, but the
machine-readable explanation was incomplete.

**Fix:** all added functions are now reported even when the overall class is
`breaking`.

### F-05 — Result-change diagnostics relied on set comparisons — Medium — Fixed

Set-based diagnostics can hide ordering information and multiplicity. The model
uses ordered tuples for result signatures, so its diagnostic path now preserves
that ordered representation and explicitly reports additions, removals, and
reordering where observable.

### F-06 — Pure compatibility logic was coupled to estate imports — Medium — Fixed

Importing the package immediately imported the `pk_core`-dependent component and
contract, preventing independent use or testing of the structural logic.

**Fix:** structural types and compatibility operations live in
`interface_model.py`; package exports for `COMPONENT` and `build_contract` are
lazy and load `pk_core` only when those estate functions are requested.

### F-07 — Limited direct unit coverage of compatibility edge cases — Medium — Fixed in part

The original archive primarily tested the 100-item component assessment path.
It had no focused dependency-free unit suite for duplicate definitions, mixed
changes, version-only changes, or strict link refusal.

**Fix:** 11 standalone unit tests now cover these cases. Fuzzing, differential
WIT parsing tests, large-corpus compatibility tests, and performance tests remain
missing and are listed separately.

### F-08 — No release integrity manifest — Low — Fixed

**Fix:** `MANIFEST.sha256` records SHA-256 digests for the hardened release
contents other than the manifest itself.

## Structural and archive checks

- ZIP path traversal: **PASS** — no entry escaped the package root.
- ZIP symlink entries: **PASS** — none detected.
- Python syntax/bytecode compilation: **PASS**.
- Checklist count: **PASS** — exactly 100 items.
- Checklist identifiers: **PASS** — 100 unique IDs.
- Checklist ordinals: **PASS** — unique contiguous range 1–100.
- Checklist/master coverage: **PASS** — every checklist ID appears in `MASTER.md`.
- Standalone model unit tests: **PASS — 11/11**.
- Optimized-mode standalone tests: **PASS — 11/11 under `python -O`**.
- Full `pk_core` component conformance: **NOT RE-RUN** — the supplied archive does
  not include the external `pk_core` dependency. The direct runner now reports
  this condition as a preflight failure rather than a successful skipped suite.

## Compatibility notes

The 4.2.0 refactor preserves the existing public structural symbols
(`Func`, `Interface`, `Incompatible`, `classify`, `check_link`) while making them
available without `pk_core`. Existing callers that request `COMPONENT` or
`build_contract` still require `pk_core`, as before. Invalid definitions that
previously produced ambiguous behavior now fail early; this is an intentional
hardening change.

## Release gate

**Local structural gate:** PASS.  
**Estate conformance gate:** PENDING EXTERNAL DEPENDENCY (`pk_core`).  
**Production completeness:** INCOMPLETE — see `MISSING_COMPONENTS.md`.

---

## 4.3.0 production-completion pass (2026-09-22)

Scope: the 40 components in `conformance/COMPONENT_CHECKLISTS.md`. The pass
built `wit/` and its tooling and dispositioned every checklist item in
`EVIDENCE_BUNDLE.json` / `LEDGER.md` (produced by `tools/evidence.py`).

Residual findings that remain open:

* **R-01 (High) — discovery path still skips pk_core conformance.** Direct
  execution of `tests/test_component.py` fails closed (exit 2), but
  `python -m unittest discover` still reports those tests as *skipped*. The CI
  workflow runs the direct form; the baseline file was left unchanged.
* **R-02 (Medium) — no independent review.** Every component gate needs a code
  and security review record that the builder cannot produce.
* **R-03 (Medium) — adjacent layers absent.** INV-09/INV-10/INV-12/GAP-15 and
  language binding toolchains are not available, so integration and
  cross-language items are BLOCKED.
* **R-04 (Low) — divergences.** Three inputs are rejected here but accepted by
  the wasm-tools 1.219.1 text parser (duplicate record fields, duplicate enum
  cases, named results). They are registered as `ours-stricter` in
  `conformance/DIVERGENCES.json` and await review.
