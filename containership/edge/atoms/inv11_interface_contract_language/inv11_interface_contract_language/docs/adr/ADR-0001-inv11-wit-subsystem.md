# ADR-0001 — INV-11 WIT interface-contract subsystem

* **Status:** PROPOSED (builder draft; approval by the accountable owner pending)
* **Date:** 2026-09-22
* **Deciders:** UNASSIGNED

## Context
INV-11 v4.2.0 was a reference model that compared synthetic Python `Func`/
`Interface` objects. Production use requires reading real WIT, resolving
packages, and classifying every change structurally, with evidence.

## Decisions
1. **Scope** — WIT text at feature level `wit-2024-10` (wasm-tools 1.219.1
   grammar) minus named results, error-context and nested namespaces; async
   and fixed lists are opt-in gates. Binding generation, linking, runtime
   marshalling, language type mapping and placement stay outside INV-11.
2. **Parser strategy** — native stdlib recursive-descent parser (no runtime
   dependency) plus continuous **differential testing** against the pinned
   reference toolchain. Rejected: shelling out to wasm-tools at runtime (adds a
   native dependency and a process boundary to every decision); Rust bindings
   via PyO3 (build complexity, platform wheels).
3. **Two models** — an immutable span-carrying syntax AST and a resolved
   semantic model keyed by canonical ids.
4. **Identity** — nominal ids `ns:pkg/item@ver#type.member`; versions select
   packages explicitly and never decide compatibility.
5. **Normalization/fingerprints** — canonical sorted-key JSON of the resolved
   model, SHA-256 with a version-tagged domain prefix (`INV11-NORM/1`).
6. **Compatibility** — a closed rule table (`INV11-COMPAT-POLICY/1`), producer
   evolution direction (old → new release); value types structural, resources
   nominal; any unknown or unresolved input fails closed.
7. **Trust** — imported contracts are digest-verified (and signature-verified
   when the profile requires) before parsing.
8. **Limits** — every stage bounded by an explicit `Limits` object.

## Consequences
No runtime dependencies; the grammar must be maintained by hand and kept
honest by the differential suite and its divergence register. Performance is
CPython-bound (see CAPACITY.md).

## Review triggers
Grammar feature-level change; reference-tool bump; any fixture
reclassification; schema major version; limit default changes.

## Realized by
`wit/parser.py`, `wit/resolve.py`, `wit/normalize.py`, `wit/compat.py`,
`tests/test_wit_*.py`, `conformance/DIVERGENCES.json`.
