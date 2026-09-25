# GAP-15 Runtime Compatibility Certification - Audit Report

**Input version:** 4.1.0  
**Remediated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** supplied `gap15_runtime_compatibility_certification` archive only

## Executive summary

The supplied package was structurally clean and syntactically valid, with a coherent 100-item checklist and a small reference implementation. The audit found one material fail-closed defect, several integrity/validation weaknesses, and a documentation mismatch. Those issues were fixed in v4.2.0 without changing the existing verdict names or removing the v4.1 string `triple` field.

The package is **not by itself a production runtime-compatibility certification service**. It models exact-triple evidence and lifecycle decisions, but major production subsystems are absent from this archive. Those are itemized in `MISSING_COMPONENTS.md`.

## Inventory and structure

Supplied v4.1.0 archive contained 8 files:

- `CHANGELOG.md`
- `README.md`
- `VERSION`
- `__init__.py`
- `component.py`
- `contract.py`
- `CHECKLIST.json`
- `tests/test_component.py`

The checklist contains exactly 100 unique requirements with contiguous ordinals 1-100, split evenly across ten dimensions. Archive paths showed no absolute-path or `../` traversal entries.

## Findings and remediation

| ID | Severity | Finding | v4.2.0 remediation |
|---|---|---|---|
| GAP15-A01 | High | Future-dated **incompatible** evidence was trusted because the clock-skew check occurred after the incompatible branch. | Timestamp plausibility is now checked before compatible or incompatible evidence is trusted; future evidence returns `untested`. |
| GAP15-A02 | High | Newer test evidence could be silently overwritten by an older record. | Older timestamps are rejected as stale/replayed evidence. |
| GAP15-A03 | High | Contradictory results with the same triple and timestamp could overwrite one another. | Same-timestamp contradiction is rejected; exact replay is idempotent. |
| GAP15-A04 | Medium | Lifecycle could regress from EOL/deprecated back to supported without explicit intent. | Lifecycle regression requires `allow_reactivation=True`. |
| GAP15-A05 | Medium | `certify()` did not validate `now`; booleans and negative/non-integer values could enter time arithmetic. | Central non-negative integer timestamp validation added. |
| GAP15-A06 | Medium | Triple identifiers accepted edge whitespace and control characters. | Identifier validation now rejects edge whitespace, control characters, empty/non-string values, and excessive length. |
| GAP15-A07 | Medium | Contract says the component owns matrix versioning, but the implementation had no matrix revision. | Monotonic matrix/lifecycle `revision` added and included in exported views and verdicts. |
| GAP15-A08 | Medium | Declared `matrix` and `lifecycle` interfaces had no deterministic exporter methods. | Added `matrix_view()` and `lifecycle_view()` using declared schema IDs. |
| GAP15-A09 | Low | Duplicate requested triples could skew coverage. | Coverage is now calculated over unique triples with input validation. |
| GAP15-A10 | Low | Caller-supplied `results`/`lifecycle` dictionaries were retained directly. | Initial state is copied and validated during construction. |
| GAP15-A11 | Low | Telemetry contract omitted the `end-of-life` verdict from its stated counter dimensions. | Contract signal text now includes `end-of-life`. |
| GAP15-A12 | Documentation | README claimed `MASTER.md` was included, but no such file existed in the supplied archive. | Inaccurate claim removed; absent source master is now explicitly tracked as missing. |

## Compatibility decisions

The following existing behavior was deliberately preserved:

- Verdict vocabulary remains `certified`, `incompatible`, `untested`, `expired`, and `end-of-life`.
- The legacy string `triple` field remains in `PK_CERTIFICATION/1` output.
- `CERTIFICATION_TTL` remains available as an alias; the explicit unit-bearing name is now `CERTIFICATION_TTL_SECONDS`.
- End-of-life runtime state continues to override a fresh passing test.
- Positive certification remains valid at exactly the TTL boundary and expires when age is greater than the TTL.
- An incompatible test result remains an incompatible result rather than becoming a positive-style `expired` certificate; production policy for ageing negative evidence is listed as a missing policy component.

## Verification performed

- ZIP path safety scan: **PASS**
- Python AST parse for all source/test files: **PASS**
- `py_compile` for all source/test files: **PASS**
- `CHECKLIST.json` parse: **PASS**
- Checklist cardinality: **100 / 100 unique IDs**
- Checklist ordinal continuity: **PASS (1-100)**
- Deterministic SHA-256 file manifest generation: **PASS**
- Isolated domain-logic smoke test with minimal `pk_core` import stubs: **PASS**
  - future negative clock skew fails closed
  - stale evidence replacement rejected
  - same-time contradiction rejected
  - exact replay idempotent
  - newer superseding evidence accepted
  - EOL override enforced
  - lifecycle regression guarded
  - deterministic schema views produced
  - duplicate coverage normalized
  - invalid/control-character identifiers rejected

## Verification limitation

`pk_core` is not bundled with this archive and was not importable in the audit environment. Therefore the full inherited `Component.assess_all()` conformance/gate behavior could not be executed against the real `pk_core` implementation. The package tests correctly skip that dependency-bound suite when `pk_core` is unavailable; this is not counted as a production conformance pass.

## Residual risks

1. `results` and `lifecycle` remain public mutable dictionaries for backward compatibility. API methods validate stored values when certifying/exporting, but direct external mutation can bypass revision increments. A production implementation should use an encapsulated transactional store.
2. Revision is an in-memory monotonic counter, not a cryptographic or durable revision identifier.
3. Test evidence has no signature, digest, provenance, tester identity, attestation reference, or immutable ledger binding.
4. The component has no trusted-time source or explicit clock-skew budget; it only rejects evidence later than supplied `now`.
5. No process/fleet concurrency control exists in this archive.
6. No real WASI/WIT/component-model negotiation engine exists; the current model certifies exact string coordinates only.
7. Full `pk_core` conformance must be re-run in the target repository before release.

## Release recommendation for this package

Treat v4.2.0 as a hardened **reference/domain component** suitable for integration and further production build-out. Do not treat the presence of 100 checklist findings as evidence that the missing operational subsystems listed in `MISSING_COMPONENTS.md` have been implemented.
