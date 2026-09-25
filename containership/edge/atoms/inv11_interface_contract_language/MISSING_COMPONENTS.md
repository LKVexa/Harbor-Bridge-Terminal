# INV-11 Interface Contract Language — Missing Components

This list distinguishes the supplied reference compatibility model from the
components required for a complete, production-grade WIT/interface-contract
language subsystem. Priority reflects architectural risk and dependency order,
not implementation effort.

## P0 — Core language and correctness gaps

1. **Real WIT lexer/parser and source loader** — parse `.wit` source rather than constructing synthetic Python `Func`/`Interface` objects.
2. **Complete WIT AST/type system** — packages, worlds, interfaces, functions, records, tuples, variants, enums, flags, options, results, lists, resources/handles, and other supported type forms.
3. **Package/world identity model** — namespace, package name, version, world selection, interface references, and canonical fully qualified identifiers.
4. **Import/include/use dependency resolver** — deterministic resolution, cycle detection, version selection, and clear conflict handling.
5. **Source-span-aware diagnostics** — file, line/column, symbol path, stable diagnostic codes, related locations, and remediation hints.
6. **Canonical structural normalization** — deterministic representation before hashing, comparison, caching, or signing.
7. **Recursive type graph handling** — graph-safe comparison with cycle guards and deterministic traversal.
8. **Complete structural compatibility rules** — type-by-type evolution rules rather than the current function/signature subset.
9. **Schema-defined machine-readable contracts** — formal schema for `PK_INTERFACE/1` and `PK_INTERFACE_DIFF/1`, including validation and evolution rules.
10. **Compatibility-policy test corpus** — positive/negative fixtures covering every supported type evolution and boundary case.

## P1 — Interoperability, assurance, and hostile-input hardening

11. **Official-tool differential testing** — compare parsing/normalization behavior against an authoritative WIT/WebAssembly component toolchain.
12. **WIT fixture corpus** — representative real-world packages, worlds, nested dependencies, resources, aliases, and versioned examples.
13. **Property-based and mutation testing** — generate structurally valid/invalid definitions and prove invariants for classification and linking.
14. **Parser/schema fuzzing** — malformed UTF-8, deep nesting, cyclic references, oversized identifiers, pathological collections, and grammar edge cases.
15. **Resource-exhaustion controls** — source-size, token-count, nesting-depth, symbol-count, graph-size, and comparison-work limits.
16. **Deterministic hashing/fingerprints** — stable interface/package fingerprints suitable for provenance and cache keys.
17. **Signed artifact/provenance verification hook** — digest/signature/SBOM/provenance checks for imported contract packages.
18. **Supported-version compatibility matrix** — explicit policy for tool version, WIT feature level, runtime/component-model version, and adjacent INV/GAP components.
19. **Adjacent-layer integration tests** — INV-09 portable compute ISA, INV-10 composition, INV-12 language interoperability, and GAP-15 runtime certification.
20. **Cross-language conformance fixtures** — generated or hand-built producer/consumer pairs proving equivalent interpretation across supported languages.

## P2 — Release engineering, performance, and operations

21. **Explicit package/build metadata** — `pyproject.toml` or equivalent with Python support range, build backend, package data, and dependency declarations.
22. **Resolvable `pk_core` dependency declaration** — documented package/version/source contract rather than path-only discovery.
23. **CI pipeline** — compile, unit, integration, optimized-mode, static analysis, fuzz-smoke, and packaging gates on every change.
24. **Static type-checking configuration** — strict typing for the compatibility core and `pk_core` adapter boundaries.
25. **Lint/security scanning policy** — reproducible code-quality and dependency-vulnerability checks with pinned tool versions.
26. **Performance benchmark harness** — measure the stated p50/p95/p99 comparison latency targets with reproducible datasets.
27. **Scale/soak tests** — thousands of packages/interfaces and large dependency graphs to expose memory growth and algorithmic hot spots.
28. **Capacity model** — expected time/memory complexity by symbol count, type graph size, and dependency fan-out.
29. **Structured telemetry adapter** — counters/histograms for definitions, classifications, refusals, parse failures, latency, and saturation.
30. **Tamper-evident audit-event emitter** — durable security/release decision records tied to artifact fingerprints.
31. **Release signing and SBOM generation** — signed release archive, dependency inventory, provenance statement, and verification instructions.
32. **Reproducible-build procedure** — deterministic archive creation and byte-for-byte validation where practical.

## P3 — Lifecycle and operator features

33. **Semantic-version recommendation engine** — optional mapping from structural diff class to recommended version change while preserving the rule that version strings do not determine compatibility.
34. **Deprecation lifecycle manager** — deprecation declaration, grace periods, consumer discovery, deadlines, and removal gates.
35. **Compatibility waiver/exception registry** — owner, rationale, scope, expiration, and audit linkage for intentional exceptions.
36. **Adapter/shim generation for supported compatible migrations** — only where semantics can be preserved mechanically.
37. **Human-readable diff renderer** — concise and expanded views grouped by package/world/interface/type/function path.
38. **Machine-readable acceptance evidence bundle** — release evidence tying requirements to tests, benchmark results, provenance, and gate verdicts.
39. **Architecture decision record (ADR)** — approved technology choice, WIT scope/version policy, compatibility philosophy, and rejected alternatives.
40. **Ownership/escalation metadata** — accountable owner, review cadence, incident escalation path, and end-of-life policy.

## External/non-goal boundaries to keep separate

The current contract correctly declares language binding generation, component
linking, runtime marshalling, language-specific type mapping, and placement as
non-owned capabilities. They should be integrated and conformance-tested here,
but not silently absorbed into INV-11 without an explicit architecture change.
