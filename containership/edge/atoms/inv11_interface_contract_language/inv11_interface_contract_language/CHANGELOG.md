# Changelog - INV-11

## 4.3.0 - 2026-09-22

Production-completion pass over the 40 missing components (checklist v4.2.0).

### Added
- `wit/` — a stdlib-only WIT front end: bounded UTF-8 source loader, spanned lexer with trivia, recursive-descent parser with recovery points, immutable AST, package/world identity, use/include/import resolver with explicit version selection and cycle paths, stable diagnostic codes, resource limits and work budgets.
- Canonical normalization (`INV11-NORM/1`) and SHA-256 fingerprints; graph-safe structural comparison; a 38-rule compatibility policy (`INV11-COMPAT-POLICY/1`) with a fixture per rule; PK_INTERFACE/1 and PK_INTERFACE_DIFF/1 JSON Schemas with a fail-closed ingestion path.
- Differential testing and component round-trips against the pinned reference toolchain wasm-tools 1.219.1; property, mutation and fuzz suites.
- Provenance verification hook (digests, SBOM, Ed25519 via OpenSSL), supported-version matrix, pk_core dependency status, telemetry, hash-chained audit log, semver advisor, deprecation manager, waiver registry, adapter planner, diff renderer, ownership record, ADR-0001.
- `pyproject.toml`, CI workflow (authored, not yet executed on a CI service), strict mypy for the core, ruff with security rules, reproducible release archive, CycloneDX SBOM, in-toto provenance, evidence bundle + verifier.

### Defects found by this pass (fixed)
- Differential testing showed `use pkg/iface@0.2.0.{x}` was rejected by the version lexer; fixed.
- A bare resource name in type position was treated as a plain reference instead of `own<R>`; fixed (found by differential testing).
- `@unstable` items were always visible; they now appear only when their feature is enabled (differential).
- `@deprecated` without `@since`/`@unstable` was accepted; now `E-GATE-PAIR` (differential).
- `async`/`future`/`stream` were accepted by default although beyond the pinned level; now opt-in (differential).
- Structurally version-independent fingerprints still embedded package versions; fixed.
- A resource member kind change was reported as a generic method change; now `func-kind-changed`.
- Same-shape named-type swaps were silent; now reported as `named-type-swapped` (compatible).
- Waiver scope matched prefix siblings (`a:b/i` covered `a:b/ix`); fixed.
- Classification re-fingerprinted whole packages on every call (75% of compare time); fingerprints are now cached per immutable `Resolved`.

### Unchanged
- `interface_model.py`, `component.py`, `contract.py`, `metadata.py` and the 4.2.0 tests.

## 4.2.0 - 2026-09-22

Audit, parsing, defect-remediation, and hardening pass.

### Correctness and safety

- Added `interface_model.py`, a dependency-free structural compatibility core with explicit validation for empty identifiers, malformed parameters, duplicate parameter names, invalid function collections, and duplicate function names.
- Duplicate function names can no longer be silently collapsed by `Interface.by_name()`.
- Change classification now reports additive edits even when a release also contains breaking edits, preserving complete diagnostics.
- Result-signature changes retain ordered semantics instead of relying on set comparison to describe the entire change.
- `check_link()` remains strict about interface identity and exact consumer-visible signatures.

### Dependency and test hardening

- Split dependency-free metadata/model imports from the `pk_core`-backed production component through lazy package exports.
- Added 11 standalone unit tests covering validation, additive/compatible/breaking classification, complete mixed-change diagnostics, and link refusal.
- Direct execution of `tests/test_component.py` now fails preflight with exit code 2 when `pk_core` is unavailable; it can no longer report a false-green run consisting only of skipped tests.
- Version metadata remains testable without `pk_core`.

### Audit artifacts

- Added `AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`, and `MANIFEST.sha256`.
- Updated evidence references in `component.py` to the new structural-model implementation paths.

### Validation status

- Python compilation: PASS.
- Dependency-free structural unit suite: 11/11 PASS under normal and optimized (`python -O`) execution.
- Full 100-item estate conformance: NOT RE-RUN in this isolated archive because `pk_core` is not bundled; direct conformance correctly fails closed until that dependency is supplied.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::check_link: linked a consumer to a producer of a differently named interface if function names matched -> raise Incompatible on name mismatch

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
