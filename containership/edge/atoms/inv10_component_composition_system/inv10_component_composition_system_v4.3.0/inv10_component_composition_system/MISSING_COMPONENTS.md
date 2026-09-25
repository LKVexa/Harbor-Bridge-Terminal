# INV-10 — Missing Components After 4.2.0 Hardening

This inventory lists components that are still absent from the supplied standalone archive after the linker correctness and hardening pass. “Missing” means the archive does not contain a production implementation/evidence artifact for the capability; it does not mean the capability cannot exist elsewhere in the broader system.

> **4.3.0 update:** each item below now has an artifact. See `DISPOSITION_4.3.0.md` for per-item status (40 implemented, 4 ports, 4 partial, 2 drafted for sign-off). This list is kept as the historical 4.2.0 baseline.

## Priority 0 — required before a production-readiness claim

1. **`pk_core` dependency package and pinned compatibility declaration** — the adapter imports `pk_core`, but the archive does not bundle it or declare an installable/pinned dependency and supported version range.
2. **Reproducible package/build metadata (`pyproject.toml` or equivalent)** — no formal Python build backend, interpreter floor/ceiling, dependency lock, wheel metadata, or reproducible-install definition is present.
3. **Machine-readable `PK_COMPONENT/1` schema** — the interface is named in prose but no JSON Schema, WIT definition, protobuf/IDL, or equivalent contract artifact is bundled.
4. **Machine-readable `PK_COMPOSITION/1` schema** — successful output has a stable shape in code, but no independently consumable schema/conformance fixture defines required/additive fields and constraints.
5. **Composition identity-profile specification** — `PK_COMPOSITION_ID/2` is implemented but still needs a formal canonicalization/digest specification, test vectors, migration rules, and compatibility policy for other implementations.
6. **Actual WebAssembly Component Model / WIT integration** — the linker currently resolves opaque interface strings; it does not parse/validate real component metadata, WIT worlds/interfaces, resources, functions, or canonical ABI constraints.
7. **INV-09 portable-compute/module-validation integration** — the contract says validated modules arrive upstream, but no adapter proves only validated artifacts can enter composition.
8. **INV-11 interface-contract/type resolver integration** — exact string matching is not a substitute for versioned typed interface compatibility, subtype/evolution rules, or schema negotiation.
9. **INV-12 language-interoperability integration** — no adapter/conformance evidence proves cross-language components can be composed safely under shared interface semantics.
10. **Application-plane (`PLN-02`) integration** — no deployment/runtime consumer demonstrates that produced order, bindings, externals, and IDs are honored during application realization.
11. **Tenant/workload/environment/site context model** — the contract declares isolation boundaries, but `Unit` and `compose()` carry no tenant/workload/site/environment identity or boundary enforcement.
12. **Authorization/capability policy engine for link decisions** — there is no policy check preventing a syntactically valid import from binding to an export the consumer is not authorized to use.
13. **Artifact provenance, signature, digest, and approved-version verification** — executable/policy artifacts are not authenticated or supply-chain verified by this component.
14. **External-import environment resolver** — `external=` declares allowed unresolved names, but no component verifies that an environment actually supplies the external interface, its version/type, trust properties, or capability policy.
15. **Declarative composition manifest loader/validator** — there is no supported file/API format for ingesting a versioned composition request with provenance, schema validation, and deterministic error reporting.
16. **Registry/discovery layer** — no authoritative component/export registry, namespace governance, lookup lifecycle, or conflict-resolution workflow exists in the archive.
17. **Persistent content-addressed composition store** — IDs are generated but there is no durable store/cache, immutability check, retrieval path, garbage collection, or corruption detection for composition records.
18. **Atomic activation and rollback controller** — the archive has no transactional promotion mechanism from candidate graph to active graph and no persisted previous-good composition state.
19. **Production evidence/gate artifacts** — no current `evidence/pk_evidence.jsonl`, `conformance/PK_GATE_RESULTS.json`, signed gate record, or equivalent machine-verifiable release evidence is bundled.
20. **Architecture decision record and accountable ownership record** — the checklist requires approved technology/function decisions, owner, escalation path, exception authority, and review cadence; these artifacts are absent.

## Priority 1 — security, reliability, and operability

21. **Tamper-evident security audit trail** — there is no append-only record of composition requests, actor identity, policy decisions, rejected bindings, published IDs, or administrative overrides.
22. **Authentication of callers/providers/control-plane actors** — the pure linker intentionally has no identity plane, and no adapter in this archive authenticates who is allowed to submit or publish a composition.
23. **Secrets/key-management integration** — no key provider, rotation strategy, encryption-at-rest/in-transit integration, or degraded behavior for unavailable identity/key/time services is present.
24. **Structured metrics exporter** — counters/gauges named in `contract.py` are not implemented; no rate/error/latency/saturation/resource metrics are emitted.
25. **Structured logging and trace propagation** — no stable operation IDs, tenant/workload/component correlation, trace-context handling, sampling, or redaction policy is implemented.
26. **Health/readiness/version/dependency status endpoint** — there is no operator-facing status surface showing active version, limits, dependency health, capability set, or readiness.
27. **Explain/diagnostic graph surface** — `bindings` improve raw explainability, but there is no operator API/report that renders dependency paths, rejected candidates, cycle paths, policy decisions, or source provenance.
28. **Config provenance and activation ledger** — `CompositionLimits` can be passed in process, but there is no versioned external configuration object recording author, source, activation time, and rollback lineage.
29. **Admission control / workload fairness controller** — static ceilings prevent extreme single requests, but there is no concurrency quota, tenant fairness, queue bound, cancellation, or load-shedding mechanism around the linker service.
30. **Crash/restart/replay semantics for a service deployment** — pure composition is stateless, but any registry/publisher service still needs idempotency keys, replay protection, duplicate-publication handling, and restart recovery.
31. **Quarantine/freeze/emergency-disable control** — there is no control-plane mechanism to block a compromised component/version/export namespace or halt publication safely.
32. **Compatibility/version matrix** — no machine-readable table defines supported Python versions, `pk_core` versions, WIT/component-model revisions, adjacent INV versions, or downgrade behavior.
33. **Migration tooling for legacy 4.1.0 composition IDs** — the release documents the identity change but does not provide an inventory/recompute/remap tool for persisted legacy IDs.
34. **Vulnerability-response / security-maintenance policy** — no supported-version window, patch SLA, CVE process, disclosure channel, or end-of-life policy is bundled.

## Priority 2 — verification, performance, and completeness

35. **Real adjacent-layer integration test suite** — the current standalone tests exercise the linker only; there are no end-to-end tests with INV-09, INV-11, INV-12, or the application plane.
36. **Property-based/fuzz harness** — the audit ran a seeded randomized DAG check, but the repository lacks a retained fuzz/property suite for malformed manifests, identifiers, graph extremes, and parser boundaries.
37. **Performance benchmark harness** — there is no reproducible benchmark proving the contract's p50/p95/p99/worst-case latency objectives, especially p99 < 200 ms at 200 components.
38. **Scale/soak/burst/overload tests** — no retained tests measure large compositions, repeated link operations, service saturation, memory growth, recovery, or long-duration stability.
39. **Fault-injection/degraded-dependency tests** — no suite exercises unavailable registry, policy, identity, provenance, storage, time, or external-interface services.
40. **Concurrency/race tests for service wrappers** — the core function is local/pure, but no tests cover concurrent publication, shared cache/store access, duplicate activation, or stale-controller races.
41. **Cross-version compatibility/conformance vectors** — there are no fixtures proving another implementation produces identical `PK_COMPOSITION_ID/2` results or consumes additive `PK_COMPOSITION/1` fields correctly.
42. **SBOM and dependency/license inventory** — the archive lacks a software bill of materials, third-party dependency inventory, license declarations, and release provenance manifest.
43. **Release signing and artifact checksums in the delivery pipeline** — this hardened archive includes a local `MANIFEST.sha256`, but there is no signing key workflow, signature envelope, trusted publisher identity, or CI verification gate.
44. **CI/CD workflow** — no automated pipeline is included for compile, unit, optimized-mode, fuzz, integration, benchmark, SBOM, signing, gate generation, and release publication.
45. **Generated API/reference documentation** — public types, error codes, limits, output fields, migration semantics, and integration examples are documented only in Markdown/source rather than a versioned generated reference site/artifact.

## Optional contract capabilities not implemented

46. **Partial/incremental composition** — no graph reuse or incremental relink engine exists.
47. **Import aliasing** — no explicit alias/rename map is supported.
48. **Dead-export elimination** — unused exports are retained and still contribute to the content identity.
49. **Nested composition object model** — the contract assumption says compositions nest, but the current successful result is a dictionary rather than a first-class `Unit`/component object with exported/imported boundary semantics.
50. **Composition diff/impact analyzer** — no tool explains how a candidate graph changes providers, externals, order, identity, or downstream workloads compared with the active graph.
