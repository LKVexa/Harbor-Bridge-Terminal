# PLN-02 Application Plane — v4.2.0 Audit Report

**Audit date:** 2026-09-22  
**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Scope:** supplied `pln02_application_plane` archive only; no network access and no external Post-Kubernetes estate was assumed.

## Executive result

The supplied package parsed successfully but was not production-complete. The
core resolver contained a material revision-identity defect: the v4.1 revision
hash covered component names, graph edges, capability bindings, and optional
drops, but did **not** cover the component capability/interface declarations
that determine composition semantics. Two interface-compatible applications
with different interface versions could therefore receive the same revision
identity. v4.2.0 closes that class by hashing the normalized semantic component
specification with full SHA-256.

The original package also relied on `pk_core` for every package import/test
path, shipped no concrete JSON Schema artifacts for the three public contracts,
accepted malformed/ambiguous graph input too loosely, did not reject unbound
imports, exposed no revision tamper check, and contained a resilience assessment
path that could still report a satisfied finding without explicitly proving both
expected refusals.

The modified package now has a standalone resolver, strict fail-closed
validation, versioned document entry points, public JSON Schemas, reference
fixtures, integrity verification, structured error codes, and dedicated resolver
tests that do not depend on `pk_core`.

## Baseline inventory

The source archive contained 8 files:

- `__init__.py`
- `component.py`
- `contract.py`
- `CHECKLIST.json`
- `README.md`
- `CHANGELOG.md`
- `VERSION`
- `tests/test_component.py`

The README stated that `MASTER.md` was present, but it was not contained in the
supplied archive.

## Defects fixed in v4.2.0

| ID | Severity | Finding | Remediation |
|---|---|---|---|
| F-01 | Critical | Revision identity omitted component interface/capability specifications. Interface version changes could preserve the same revision ID. | Added normalized `component_specs` to revision content and hash input; switched to full SHA-256. |
| F-02 | High | Declared imports could remain unbound and still yield a revision. | Every import must now have exactly one incoming compatible edge. |
| F-03 | High | Multiple producers could target the same consumer/interface with no ambiguity refusal. | Ambiguous imports now fail with `INCOMPATIBLE_INTERFACE`. |
| F-04 | High | Input structure/types were weakly validated; malformed mappings, flags, identifiers, edges, and providers could crash or be silently accepted. | Added bounded fail-closed validation with `INVALID_APPLICATION`. |
| F-05 | High | Unsupported component fields were silently ignored by the revision identity. | Unknown component/envelope fields are rejected instead of omitted from semantics. |
| F-06 | High | Revision objects could be modified after resolution with no integrity check. | Added `verify_revision()` and `REVISION_INTEGRITY_ERROR`. |
| F-07 | Medium | Revision hashes were truncated to 32 hex characters. | Full 64-character SHA-256 addresses are now emitted. |
| F-08 | Medium | Duplicate graph edges were accepted and altered revision identity without adding semantics. | Duplicate edges are rejected. |
| F-09 | Medium | Capability requirement values were treated by truthiness rather than required to be booleans. | Requirement flags must be literal booleans. |
| F-10 | Medium | Provider IDs were accepted without structural validation. | Provider/capability identifiers are validated and bounded. |
| F-11 | Medium | Public contract names existed only as strings in the contract; no schema files or versioned envelope parser were shipped. | Added Draft 2020-12 schemas and `resolve_document()`. |
| F-12 | Medium | Package import was unnecessarily coupled to `pk_core`, preventing standalone resolver use/test. | Moved resolver to dependency-free `resolver.py`; conformance adapter is lazy-loaded. |
| F-13 | Medium | Resilience assessment counted expected exceptions but did not explicitly fail if either refusal stopped occurring. | Added `else` failure paths and a `proven == 2` verification. |
| F-14 | Medium | Existing tests could all skip when `pk_core` was absent, leaving the actual resolver untested. | Added standalone resolver test suite with deterministic/integrity/validation cases. |
| F-15 | Low | README claimed a `MASTER.md` artifact that was absent. | Corrected documentation and recorded the source artifact as missing rather than fabricating it. |
| F-16 | High | `component:capability` binding keys were potentially ambiguous because `:` was accepted inside component names. | Reserved `:` out of component names in code and schemas, preventing namespace-key collisions. |

## Files added or materially changed

- `resolver.py` — standalone deterministic resolver and validation/integrity layer
- `schemas/PK_APPLICATION-1.schema.json`
- `schemas/PK_PROVIDER_CATALOGUE-1.schema.json`
- `schemas/PK_APPLICATION_REVISION-1.schema.json`
- `tests/test_resolver.py`
- `tests/fixtures/application.json`
- `tests/fixtures/catalogue.json`
- `__init__.py` — lazy `pk_core` integration and resolver exports
- `component.py` — conformance adapter uses hardened resolver
- `README.md`, `CHANGELOG.md`, `VERSION`
- `AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`

## Verification performed

1. `python -m compileall -q .` — **PASS**.
2. `python -m unittest discover -s tests -p 'test_*.py' -v` — resolver tests pass; the three `pk_core` conformance tests skip because the dependency is absent from the supplied archive.
3. `python -O tests/test_resolver.py` — **PASS**, proving resolver behavior does not depend on removable `assert` statements.
4. Draft 2020-12 JSON Schema meta-validation and fixture/generated-revision validation — **PASS** when the optional `jsonschema` test dependency is available in the audit environment.
5. Production Python AST scan for bare `assert`, direct `eval`/`exec`, and simple hard-coded-secret patterns — **no findings**.
6. 1,000 deterministic randomized resolver exercises — **PASS**; successful revisions verified and caller input objects remained unchanged.

## Important verification limitation

The archive does **not** contain `pk_core`. Therefore the full 100-finding
`ApplicationPlaneComponent.assess_all()` result, sibling integration behavior,
`pk_core gate`, and evidence-ledger verification could not be executed in this
standalone audit. The existing `tests/test_component.py` correctly reports this
as skipped rather than a false pass.

`ruff` and `pyright` were also not installed in the audit environment. Their
absence is not reported as a clean lint/type-check result; a stdlib AST/static
pattern scan and Python compilation were run instead.

## Post-hardening conclusion

The v4.2.0 resolver core is materially safer and more testable than v4.1.0, but
the package is still an architectural component/reference implementation rather
than a complete production application-plane service. The remaining missing
components are enumerated, grouped, and mapped to checklist requirements in
`MISSING_COMPONENTS.md`.
