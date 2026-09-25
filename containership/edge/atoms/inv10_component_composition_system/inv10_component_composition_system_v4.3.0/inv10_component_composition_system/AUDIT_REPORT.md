# INV-10 Component Composition System — Audit Report

**Input version:** 4.1.0  
**Hardened version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** all files in the supplied `inv10_component_composition_system.zip`; code was inspected before any bundled implementation was executed.

## Executive result

The archive was structurally valid and Python-compilable, but two correctness defects prevented the linker from meeting its own dependency-cycle and content-addressed-identity claims. The hardening pass fixes those defects, isolates the pure linker from the external `pk_core` framework, adds validation/resource ceilings/structured errors, expands deterministic binding metadata, and adds a standalone test suite.

The revised archive is suitable as a substantially stronger reference linker. It is **not independently production-certified** from this archive alone because `pk_core`, adjacent architectural elements, integration evidence, schemas, operational controls, and several security/observability components are not bundled. Those residual gaps are enumerated in `MISSING_COMPONENTS.md`.

## Findings and disposition

| ID | Severity | Finding | Disposition in 4.2.0 |
|---|---|---|---|
| A-01 | Critical | Self-import edges were removed with `deps - {component.name}`. A component could import its own export and evade the stated cycle refusal. | Fixed. Self-edges remain in the graph and are rejected as `COMPOSITION_CYCLE`, with a deterministic cycle path. |
| A-02 | High | The 4.1.0 digest used only component names, topological order, external imports, and export interface names. Different binding graphs could therefore receive the same composition ID. | Fixed. Identity material now contains normalized units, their imports/exports, resolved bindings, and used externals. |
| A-03 | High | Composition IDs were truncated to 24 hexadecimal characters (96 bits), weakening collision resistance for a content-addressed identifier. | Fixed. Full SHA-256 is returned and the identity profile is labeled `PK_COMPOSITION_ID/2`. |
| A-04 | High | Component/interface strings were accepted without type, whitespace, normalization, control-character, or length validation, despite the contract identifying crafted interface names as an injection threat. | Fixed. Fail-closed identifier validation added. |
| A-05 | High | No graph-size/resource ceilings existed, allowing a hostile or accidental request to allocate/sort very large graphs. | Fixed. Immutable `CompositionLimits` added and checked before/while graph construction. |
| A-06 | Medium | Failure types were Python exceptions only and did not expose stable machine-readable codes/details. | Fixed. All composition failures derive from `CompositionError` and provide `as_dict()`. |
| A-07 | Medium | Successful output did not expose which provider satisfied each import, reducing auditability/explainability. | Fixed. Added deterministic `providers` and `bindings`. |
| A-08 | Medium | The linker lived in `component.py`, which imported `pk_core`; therefore even core link behavior was not directly testable from the standalone archive. | Fixed. Pure linker moved to dependency-free `composition.py`; `pk_core` adapter is lazy-loaded. |
| A-09 | Medium | Existing tests primarily verified the checklist adapter and were completely skipped when `pk_core` was absent. | Fixed for linker logic. Added 12 stdlib tests that run without `pk_core`; framework conformance remains dependency-bound. |
| A-10 | Medium | The 4.1.0 changelog stated all 100 requirements were satisfied, but the supplied standalone archive lacks `pk_core` and retained gate/evidence artifacts needed to reproduce that claim. | Historical text preserved, but 4.2.0 explicitly does not repeat the certification claim without reproducible evidence. |
| A-11 | Low | Core element constants were coupled to `contract.py`, which itself imports `pk_core`. | Fixed. Dependency-free `metadata.py` is now the shared source for element identity. |
| A-12 | Low | Evidence references in the adapter pointed to `component.py::compose` after linker extraction. | Fixed. References now identify `composition.py::compose`. |

## Identity migration

4.2.0 intentionally changes composition IDs. The 4.1.0 ID was not a complete graph address: two compositions with the same component names, compatible topological order, external-import list, and export-name set could collide even when a consumer bound to a different provider/interface graph. 4.2.0 hashes canonical JSON containing the complete normalized unit declarations and bindings.

Downstream systems should persist the `identity_profile` alongside the composition ID. Do not compare a 4.1.0 legacy ID with a `PK_COMPOSITION_ID/2` ID as though they were generated under identical semantics.

## Validation performed

- ZIP entries were checked for path traversal before extraction.
- `python -m py_compile` passed for package modules and tests.
- `python tests/test_linker.py` passed all 12 standalone tests.
- `python -O tests/test_linker.py` passed all 12 standalone tests, confirming optimized mode does not remove the core verification behavior.
- A seeded 1,000-case randomized DAG pass verified input-order-independent composition IDs and provider-before-consumer topological order.
- `python tests/test_component.py` completed with 3 skips because `pk_core` is not present in the standalone archive.

## Residual risk / non-claims

This pass does not claim that the 100-item production checklist is freshly certified. The archive still lacks the full external framework and production evidence needed to validate adjacent-layer integration, authentication/authorization, provenance, tenant enforcement, telemetry, performance SLOs, rollout/rollback, operational governance, and other requirements. See `MISSING_COMPONENTS.md`.
