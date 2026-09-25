# INV-10 4.3.0 — disposition of the 50 missing components

Status key: **IMPLEMENTED** code + tests in this archive · **PORT** fail-closed interface + reference adapter; real adjacent service still needed · **PARTIAL** usable, with a stated gap · **DRAFTED** document that needs owner sign-off.

No checklist box in `INV10_50_COMPONENT_PROFESSIONAL_CHECKLISTS_v1.0.0.md` has been ticked on your behalf. That checklist asks for owner, reviewer and approval evidence, which a build cannot supply. The table below points to the artifact that answers each component-specific item.

| # | Component | Artifact(s) | Status | Notes |
|---|---|---|---|---|
| 01 | pk_core pin | `pkcore_compat.py; pyproject [pkcore] extra; docs/COMPATIBILITY.json` | PARTIAL | Range declared + fail-closed gate + surface lock; pk_core itself not bundled so range is unqualified |
| 02 | build metadata | `pyproject.toml; requirements.lock` | IMPLEMENTED | Wheel built and installed into a clean venv; `inv10` entry point runs |
| 03 | PK_COMPONENT/1 schema | `schemas/PK_COMPONENT-1.schema.json; schemas.validate_component` | IMPLEMENTED | Closed schema; round-trip + rejection tests |
| 04 | PK_COMPOSITION/1 schema | `schemas/PK_COMPOSITION-1.schema.json; schemas.validate_composition` | IMPLEMENTED | Additive fields tolerated; order/binding invariants checked |
| 05 | identity-profile spec | `docs/IDENTITY_PROFILE.md; conformance/vectors.json` | IMPLEMENTED | Spec re-implemented independently in tests and matches every vector |
| 06 | WIT / Component Model | `wit.py` | PARTIAL | Bounded WIT-subset parser (package/interface/world/include, resources, types, funcs) -> Units; no binary component parsing or canonical-ABI checks (INV-09's job) |
| 07 | INV-09 integration | `adapters.ModuleValidator / require_validated` | PORT | Fail-closed port + reference validator; real INV-09 service not available |
| 08 | INV-11 integration | `adapters.InterfaceResolver / resolve_interfaces` | PORT | Semver resolver with explicit rewrite record; real INV-11 not available |
| 09 | INV-12 integration | `adapters.check_language_interop` | PORT | ABI-family matrix check; real INV-12 not available |
| 10 | PLN-02 integration | `adapters.realization_plan / verify_realization` | PORT | Plan + conformance oracle; no real runtime consumer |
| 11 | context model | `governance.CompositionContext / enforce_tenant_boundary` | IMPLEMENTED |  |
| 12 | link policy engine | `governance.LinkPolicy` | IMPLEMENTED | Default-deny, deny-wins, versioned |
| 13 | provenance/signature | `governance.ProvenanceVerifier` | IMPLEMENTED | HMAC-SHA256 (stdlib); asymmetric verifier needed for third-party trust (ADR-0001 §2) |
| 14 | external resolver | `governance.EnvironmentResolver` | IMPLEMENTED | Version-compatible + trust floor |
| 15 | manifest loader | `manifest.py; schemas/PK_COMPOSITION_MANIFEST-1.schema.json` | IMPLEMENTED | Size/depth bounds, duplicate keys, path-addressed errors |
| 16 | registry | `controlplane.Registry` | IMPLEMENTED | In-process; persistence left to deployment |
| 17 | content-addressed store | `controlplane.CompositionStore` | IMPLEMENTED | Verified reads recompute the address; fsck; gc |
| 18 | activation/rollback | `controlplane.ActivationController` | IMPLEMENTED | Atomic pointer, CAS generations, previous-good lineage |
| 19 | evidence/gate artifacts | `tools/gen_evidence.py; evidence/pk_evidence.jsonl; conformance/PK_GATE_RESULTS.json` | IMPLEMENTED | Overall verdict CONDITIONAL_GO (computed); unsigned in this archive |
| 20 | ADR + ownership | `docs/ADR-0001-inv10-composition.md; docs/OWNERSHIP.md` | DRAFTED | Owner/approver fields blank by design - needs David's signature |
| 21 | audit trail | `security.AuditTrail` | IMPLEMENTED | Hash chain, fsync, redaction, tamper test |
| 22 | authentication | `security.Authenticator / ROLE_PERMISSIONS` | IMPLEMENTED | HMAC tokens, expiry, role actions |
| 23 | key management | `security.KeyProvider` | IMPLEMENTED | Rotation/retire/revoke/degraded; KMS/HSM backing is a deployment task |
| 24 | metrics | `observability.Metrics` | IMPLEMENTED | Contract signals + latency histogram, Prometheus text, cardinality cap |
| 25 | logs + tracing | `observability.StructuredLogger / child_traceparent` | IMPLEMENTED | W3C traceparent, sampling, redaction |
| 26 | health/readiness | `observability.health_report; CompositionService.health` | IMPLEMENTED | Function surface; HTTP binding is a deployment task |
| 27 | explain surface | `observability.explain; `inv10 explain`` | IMPLEMENTED |  |
| 28 | config ledger | `controlplane.ConfigLedger` | IMPLEMENTED |  |
| 29 | admission control | `controlplane.AdmissionController` | IMPLEMENTED | Concurrency, per-tenant, bounded queue, deadlines, shedding |
| 30 | restart/replay | `CompositionService idempotency journal + nonces` | IMPLEMENTED | Nonce set is in-memory (per process) |
| 31 | quarantine/freeze | `controlplane.QuarantineList; CompositionService.quarantine_*/set_frozen` | IMPLEMENTED | Audited, role-gated |
| 32 | compatibility matrix | `docs/COMPATIBILITY.json` | IMPLEMENTED | Only Python 3.11 verified here; CI matrix covers 3.10-3.13 |
| 33 | 4.1.0 migration | `features.migrate_legacy; `inv10 migrate`` | PARTIAL | Recompute from persisted units; legacy formula reconstructed from the audit text, used as corroboration only |
| 34 | security policy | `SECURITY.md` | DRAFTED | SLAs proposed; needs owner acceptance |
| 35 | adjacent integration tests | `tests/test_verification.py::TestIntegrationPipeline` | PARTIAL | End-to-end through all ports with reference adapters, not the real services |
| 36 | property/fuzz | `TestPropertyFuzz` | IMPLEMENTED | Seeded; INV10_FUZZ_CASES scales in nightly CI |
| 37 | benchmark | `tools/bench.py` | IMPLEMENTED | p99 well under 200 ms at 200 components on this host |
| 38 | scale/soak/burst | `TestScaleSoak` | IMPLEMENTED | 4,000-component link, memory-growth soak, burst shedding |
| 39 | fault injection | `TestFaultInjection` | IMPLEMENTED |  |
| 40 | concurrency/race | `TestConcurrency` | IMPLEMENTED | Cross-process locking of the activation pointer is emulated with a shared lock |
| 41 | conformance vectors | `conformance/vectors.json; tools/gen_vectors.py` | IMPLEMENTED | CI fails on identity drift |
| 42 | SBOM | `sbom.cdx.json; tools/gen_sbom.py` | IMPLEMENTED | Project licence UNDECLARED - owner decision |
| 43 | release signing | `tools/sign_release.py` | IMPLEMENTED | Tool verified with a throwaway key; this archive ships unsigned |
| 44 | CI/CD | `.github/workflows/inv10.yml` | IMPLEMENTED | Not yet run on GitHub |
| 45 | API reference | `docs/api/INV10_API_REFERENCE_4.3.0.md; tools/gen_docs.py` | IMPLEMENTED |  |
| 46 | incremental composition | `features.IncrementalLinker` | IMPLEMENTED | Cache + affected-set; the link itself is still full (correctness first) |
| 47 | import aliasing | `features.apply_aliases / compose_extended` | IMPLEMENTED |  |
| 48 | dead-export elimination | `features.eliminate_dead_exports` | IMPLEMENTED | Opt-in; changes the id by design |
| 49 | nested composition | `features.as_unit / compose_nested` | IMPLEMENTED | tree_digest binds inner ids |
| 50 | diff/impact analyzer | `features.diff; `inv10 diff`` | IMPLEMENTED |  |

**Totals:** DRAFTED 2, IMPLEMENTED 40, PARTIAL 4, PORT 4
