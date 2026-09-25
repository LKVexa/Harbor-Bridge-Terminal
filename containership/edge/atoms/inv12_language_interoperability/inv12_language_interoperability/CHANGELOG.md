# Changelog - INV-12

## 4.3.0 - 2026-09-22

Execution of `INV12_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST_v1.0.0` (58 components, 3,550 items).
Additive: the legacy `lower`/`lift`/`check_mapping`/`COMPONENT` API and its behaviour are unchanged.

### Added
- `canon/` stdlib-only canonical interop engine: WIT-subset schema loader and type AST (MC-001), full primitive set incl. s8/u16/s16/char (MC-002), tuple/enum/flags (MC-003), resource handles with generations and own/borrow call scopes (MC-004/005), recursive path-aware validator (MC-006), versioned language registry with profile digest (MC-007), `exact/1` numeric policy (MC-008), strict Unicode/UTF-16 transcoding (MC-009), canonical ABI layout + flattening (MC-010), checked guest memory and realloc/post-return lifecycle (MC-011/012), variant/option/result wire model (MC-013), `PK_INTEROP_ERROR/1` envelope (MC-014), negotiation and evolution (MC-015/016), futures/streams (MC-017), schema-derived limits (MC-018).
- Operational controls: bounded-cardinality metrics, traces, HMAC hash-chained audit, health, fair-share capacity (MC-037..042); config schema, quorum-approved atomic activation/rollback, provenance, key rotation/revocation (MC-043..045); artifact policy, CycloneDX SBOM, dependency lock (MC-046/047); capability gate + trust-outage policy (MC-048/049).
- `canon/boundary.py` reference runtime adapter and Python binding (MC-019 seam, MC-023).
- Rust, Go, JavaScript fixture bindings (MC-020..022); golden corpus of 50 valid + 17 invalid vectors (MC-026); 4-language conformance matrix and differential tester (MC-024/029); Go→wasip1 guest executed in V8 with host lift/lower over real linear memory (MC-011/012/019 evidence).
- Property tests, coverage-guided fuzzer with persisted regressions, malicious-memory, concurrency and leak suites (MC-027..032); benchmark / SLO / DoS harness (MC-034..036).
- One-command CI with negative pipeline test, GitHub Actions matrix, release evidence bundle (MC-053..055).
- Docs: SPEC, ADR-0001, THREAT_MODEL, TRACEABILITY, COMPATIBILITY, RUNBOOK, INCIDENT_PLAYBOOK, OPERATIONS (MC-050..052, 056..058).
- `CHECKLIST_MC_STATUS.md`: every checklist item executed and annotated; `[x]` only with cited evidence.

### Changed
- Package `__init__` imports the `pk_core`-bound component lazily so `canon` works without the parent framework.

### Not done (see `MISSING_COMPONENTS.md`)
- Production Component Model runtime adapter, adjacent-layer (INV-10/11/13/45) fixtures, multi-platform execution, sanitizers, signatures, hosted CI, `pk_core` gate, named owners and peer review.

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening, and version-bump pass.

### Correctness fixes

- Fixed the no-shared-memory claim for mutable data: `lower()` now snapshots data-only trees and `lift()` returns a second detached copy instead of reusing the caller's object graph.
- Replaced publicly mutable canonical transfer state with encapsulated, lock-guarded single-move ownership semantics.
- Added strict UTF-8 validation so lone surrogate code points cannot cross a nominal `string` boundary.
- Added exact f32 representability checks, preventing silent f64-to-f32 rounding.
- Corrected the JavaScript integer capability profile to include exact signed/unsigned 64-bit mappings via BigInt semantics.

### Security / resilience hardening

- Reject arbitrary host objects instead of calling user-controlled `__deepcopy__` behavior.
- Reject cyclic values and bound canonicalization by nesting depth, per-container item count, total node count, string size, and owner-identifier size.
- Made language/type mapping and integer-range registries read-only.
- Validate ownership identifiers and `CanonicalValue` inputs; refuse invalid canonical objects before transfer.
- Expanded behavioral assessment so the no-alias claim is actually exercised with a nested mutable value.

### Verification

- Expanded stdlib tests for nested alias isolation, cyclic input refusal, custom-object refusal, invalid Unicode, f32 loss refusal, JavaScript 64-bit integer support, and concurrent double-lift protection.
- Added `AUDIT.md` and `MISSING_COMPONENTS.md` to separate implemented guarantees from remaining production work.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::lower: bool accepted as an integer type (bool subclasses int) -> refused with OutOfRange
- component.py::lower: 'bool' type accepted any value -> require a real bool

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
