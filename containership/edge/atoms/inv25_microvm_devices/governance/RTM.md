# INV-25 Requirements Traceability Matrix

Generated from `tools/rtm_source.py` by `python tools/rtm.py build`. Do not edit by hand.

| Check | Status | Artifacts | Tests | Reason |
|---|---|---|---|---|
| INV-25-C001 | PASS | contract.py::build.responsibility<br>README.md |  |  |
| INV-25-C002 | PASS | contract.py::build.owns<br>docs/ownership.md |  |  |
| INV-25-C003 | PASS | contract.py::build.dependencies<br>docs/ownership.md | IntegrationContractTest |  |
| INV-25-C004 | PASS | contract.py::build.source_of_truth<br>store.py::CatalogueStore.active | ActivationTest |  |
| INV-25-C005 | PASS | contract.py::build.assumptions<br>ADR/ADR-0001-virtio-net-block.md |  |  |
| INV-25-C006 | PASS | contract.py::build.boundaries<br>authz.py::authorize | AuthorizationTest |  |
| INV-25-C007 | PASS | contract.py::build.mandatory<br>contract.py::build.optional |  |  |
| INV-25-C008 | PASS | contract.py::build.non_goals<br>README.md |  |  |
| INV-25-C009 | BLOCKED | docs/ownership.md<br>CODEOWNERS<br>docs/incident-response.md | GovernanceTest | role-based ownership defined; named team/person assignments requires named human approval that cannot be minted by tooling (see governance/waivers.json) |
| INV-25-C010 | BLOCKED | ADR/ADR-0001-virtio-net-block.md |  | ADR drafted with status Proposed; requires named human approval that cannot be minted by tooling (see governance/waivers.json) |
| INV-25-C011 | PASS | model.py<br>README.md | DeviceModelTest<br>ErrorContractTest |  |
| INV-25-C012 | PASS | docs/requirements.md | DeviceModelTest |  |
| INV-25-C013 | PASS | docs/requirements.md<br>conformance/performance/thresholds.json | PerformanceTest |  |
| INV-25-C014 | PASS | docs/error-contract.md<br>errors.py::CODES | ErrorContractTest |  |
| INV-25-C015 | PASS | docs/requirements.md<br>store.py::CatalogueStore | ActivationTest |  |
| INV-25-C016 | PASS | docs/compatibility.md<br>compat.py::negotiate | CompatTest |  |
| INV-25-C017 | PASS | docs/limits.md<br>model.py::MAX_DEVICES | LimitsTest |  |
| INV-25-C018 | PASS | docs/requirements.md<br>store.py::CatalogueStore.activate | PersistenceAndFaultTest |  |
| INV-25-C019 | PASS | docs/requirements.md |  |  |
| INV-25-C020 | PASS | governance/RTM.json<br>tools/rtm.py | RtmTest |  |
| INV-25-C021 | PASS | docs/interfaces.md | SchemaTest |  |
| INV-25-C022 | PASS | schemas/ | SchemaTest |  |
| INV-25-C023 | PASS | docs/authn-authz.md<br>authz.py::Verifier | AuthnTest |  |
| INV-25-C024 | PASS | docs/authn-authz.md<br>authz.py::authorize | AuthorizationTest<br>ActivationTest |  |
| INV-25-C025 | PASS | docs/interfaces.md<br>store.py::_Bucket | ActivationTest |  |
| INV-25-C026 | PASS | docs/error-contract.md<br>schemas/PK_DEVICE_ERROR_1.schema.json | ErrorContractTest |  |
| INV-25-C027 | PASS | docs/compatibility.md<br>compat.py | CompatTest |  |
| INV-25-C028 | PASS | docs/limits.md | LimitsTest<br>ActivationTest |  |
| INV-25-C029 | PASS | conformance/fixtures/<br>conformance/integration/peer_contracts.py | SchemaTest<br>IntegrationContractTest |  |
| INV-25-C030 | EXTERNAL | conformance/integration/peer_contracts.py | IntegrationContractTest | INV-25 side proven against version-pinned contract fixtures; real INV-24/35/26/GAP-13 evidence is peer-owned |
| INV-25-C031 | BLOCKED | ADR/ADR-0001-virtio-net-block.md<br>compat.py::MATRIX | CompatTest | virtio 1.2 proposed; VMM/backend implementation versions not yet pinned by owners |
| INV-25-C032 | PASS | docs/requirements.md<br>store.py::Snapshot | ActivationTest |  |
| INV-25-C033 | PASS | docs/limits.md<br>model.py | DeviceModelTest |  |
| INV-25-C034 | PASS | store.py::CatalogueStore.activate<br>model.py::catalogue_from_export | ActivationTest<br>PersistenceAndFaultTest |  |
| INV-25-C035 | PASS | store.py::CatalogueStore.__init__ | AuthorizationTest |  |
| INV-25-C036 | PASS | schemas/PK_DEVICE_CONFIG_ACTIVATION_1.schema.json<br>store.py::CatalogueStore._record | ActivationTest |  |
| INV-25-C037 | PASS | store.py::CatalogueStore._commit | ActivationTest<br>PersistenceAndFaultTest<br>ConcurrencyTest |  |
| INV-25-C038 | PASS | store.py::CatalogueStore.rollback<br>docs/rollout.md | ActivationTest |  |
| INV-25-C039 | PASS | errors.py::_redact<br>audit.py::_FORBIDDEN_KEYS | ErrorContractTest<br>AuditTamperTest |  |
| INV-25-C040 | PASS | docs/runbooks.md<br>pk_bootstrap.py | CompatTest |  |
| INV-25-C041 | PASS | docs/threat-model.md | FuzzTest<br>AuthnTest |  |
| INV-25-C042 | PASS | authz.py::CAPABILITIES | AuthorizationTest |  |
| INV-25-C043 | PASS | docs/threat-model.md<br>model.py | DeviceModelTest | package performs no network/device I/O; state file path is explicit |
| INV-25-C044 | PASS | authz.py::Verifier<br>provenance.py::TrustPolicy | AuthnTest<br>ProvenanceTest |  |
| INV-25-C045 | PASS | provenance.py::TrustPolicy.verify<br>docs/provenance.md | ProvenanceTest |  |
| INV-25-C046 | EXTERNAL | contract.py::build.not_owns |  | execution/memory isolation is owned by INV-24/INV-35; INV-25 bounds guest-visible surface only |
| INV-25-C047 | EXTERNAL | docs/threat-model.md |  | catalogue holds no secrets; transport/at-rest encryption owned by control-plane storage and transport |
| INV-25-C048 | PASS | docs/authn-authz.md | AuthnTest<br>PersistenceAndFaultTest |  |
| INV-25-C049 | PASS | audit.py::AuditLog<br>schemas/PK_DEVICE_AUDIT_EVENT_1.schema.json | AuditTamperTest<br>ActivationTest |  |
| INV-25-C050 | PASS | tests/test_fuzz.py<br>tests/test_authz.py | FuzzTest<br>AuthnTest<br>AuthorizationTest |  |
| INV-25-C051 | PASS | docs/failure-model.md | PersistenceAndFaultTest |  |
| INV-25-C052 | PASS | store.py::CatalogueStore.health<br>docs/telemetry-policy.md | ActivationTest |  |
| INV-25-C053 | PASS | docs/error-contract.md | ErrorContractTest | INV-25 performs no internal retries; retryable flag + guidance for callers |
| INV-25-C054 | PASS | store.py::_Bucket<br>store.py::CatalogueStore.MAX_PENDING | ActivationTest |  |
| INV-25-C055 | NOT_APPLICABLE | docs/failure-model.md |  | single-writer reference store; no failover replica in scope (waiver W-0004) |
| INV-25-C056 | PASS | docs/failure-model.md<br>store.py::CatalogueStore.permits | PersistenceAndFaultTest |  |
| INV-25-C057 | PASS | store.py::CatalogueStore._persist | PersistenceAndFaultTest |  |
| INV-25-C058 | PASS | store.py::CatalogueStore.activate | ConcurrencyTest | CAS on expected digest; multi-process deployment requires external CAS store |
| INV-25-C059 | PASS | store.py::CatalogueStore.emergency_disable | ActivationTest<br>IntegrationContractTest |  |
| INV-25-C060 | PASS | tests/test_store.py | PersistenceAndFaultTest |  |
| INV-25-C061 | PASS | conformance/performance/bench.py<br>evidence/benchmarks/ | PerformanceTest | baseline from one Linux x86_64 host; pinned host profile BLOCKED on owner hardware |
| INV-25-C062 | BLOCKED | conformance/performance/thresholds.json | PerformanceTest | thresholds proposed; requires named human approval that cannot be minted by tooling (see governance/waivers.json) |
| INV-25-C063 | PASS | conformance/performance/bench.py | PerformanceTest<br>ConcurrencyTest | steady/burst/max-catalogue measured; fleet scale-out is peer-owned |
| INV-25-C064 | PASS | conformance/performance/bench.py | PerformanceTest |  |
| INV-25-C065 | PASS | docs/requirements.md |  |  |
| INV-25-C066 | NOT_APPLICABLE |  |  | control-plane catalogue; kernel-bypass/zero-copy belong to INV-35 datapath |
| INV-25-C067 | PASS | docs/limits.md | LimitsTest |  |
| INV-25-C068 | NOT_APPLICABLE |  |  | no edge-node deployment of the catalogue service declared |
| INV-25-C069 | PASS | docs/limits.md<br>store.py::CatalogueStore.signals | ActivationTest |  |
| INV-25-C070 | BLOCKED | .github/workflows/ci.yml<br>conformance/performance/bench.py | PerformanceTest | enforced in CI once thresholds are approved (item 62) |
| INV-25-C071 | PASS | store.py::CatalogueStore.health | ActivationTest |  |
| INV-25-C072 | PASS | store.py::CatalogueStore.signals | ActivationTest |  |
| INV-25-C073 | PASS | audit.py::AuditLog.emit<br>docs/telemetry-policy.md | AuditTamperTest |  |
| INV-25-C074 | PASS | store.py<br>conformance/integration/peer_contracts.py | IntegrationContractTest | correlation_id propagated through store, audit and runtime fixture; W3C trace export owned by host service |
| INV-25-C075 | PASS | errors.py::_redact | ErrorContractTest |  |
| INV-25-C076 | PASS | store.py::CatalogueStore._record | ActivationTest |  |
| INV-25-C077 | PASS | store.py::CatalogueStore.explain | ActivationTest |  |
| INV-25-C078 | PASS | schemas/PK_DEVICE_CONFIG_ACTIVATION_1.schema.json | ActivationTest | source_revision/build_id recorded; live infrastructure graph is external |
| INV-25-C079 | PASS | docs/telemetry-policy.md |  |  |
| INV-25-C080 | BLOCKED | docs/telemetry-policy.md |  | dashboard/alert definitions provided; deployment to the owner's monitoring stack not possible here |
| INV-25-C081 | PASS | tests/ | DeviceModelTest<br>ActivationTest |  |
| INV-25-C082 | PASS | schemas/ | SchemaTest<br>ErrorContractTest |  |
| INV-25-C083 | EXTERNAL | conformance/integration/peer_contracts.py | IntegrationContractTest | same as C030 |
| INV-25-C084 | BLOCKED | docs/compatibility.md | CompatTest | only linux/x86_64 CPython exercised; arm64/hypervisor cells need owner hardware |
| INV-25-C085 | PASS | tests/test_fuzz.py<br>conformance/fuzz/regressions.json | FuzzTest |  |
| INV-25-C086 | PASS | docs/concurrency.md | ConcurrencyTest |  |
| INV-25-C087 | PASS | docs/threat-model.md | AuthnTest<br>AuthorizationTest<br>ProvenanceTest<br>FuzzTest |  |
| INV-25-C088 | PASS | conformance/performance/bench.py | PerformanceTest | soak/fleet-scale runs are scheduled jobs |
| INV-25-C089 | PASS | tests/test_store.py | PersistenceAndFaultTest<br>IntegrationContractTest |  |
| INV-25-C090 | BLOCKED | docs/acceptance-policy.md<br>tools/gate.py | RtmTest | pk_core-driven assessment not executable: pk_core not distributed with this archive (work item 1) |
| INV-25-C091 | PASS | contract.py::build.slos<br>SUPPORT.md |  |  |
| INV-25-C092 | PASS | docs/rollout.md<br>store.py::CatalogueStore.emergency_disable | ActivationTest<br>IntegrationContractTest |  |
| INV-25-C093 | PASS | docs/compatibility.md<br>compat.py::MATRIX | CompatTest |  |
| INV-25-C094 | PASS | SECURITY.md<br>docs/vulnerability-eol.md | GovernanceTest |  |
| INV-25-C095 | PASS | docs/runbooks.md<br>store.py::CatalogueStore._load | PersistenceAndFaultTest |  |
| INV-25-C096 | PASS | docs/runbooks.md |  |  |
| INV-25-C097 | BLOCKED | docs/incident-response.md |  | paging targets/on-call rota requires named human approval that cannot be minted by tooling (see governance/waivers.json) |
| INV-25-C098 | BLOCKED | governance/reviews.json<br>docs/recurring-review.md | GovernanceTest | cadence and register defined; first review must be held and recorded by the owner |
| INV-25-C099 | PASS | governance/waivers.json | GovernanceTest |  |
| INV-25-C100 | BLOCKED | docs/acceptance-policy.md<br>tools/gate.py | RtmTest | pk_core-driven assessment not executable: pk_core not distributed with this archive (work item 1); approvals and signing key not available |

**Totals:** BLOCKED 11, EXTERNAL 4, NOT_APPLICABLE 3, PASS 82

| Dimension | BLOCKED | EXTERNAL | FAIL | NOT_APPLICABLE | PASS |
|---|---|---|---|---|---|
| Architecture & Scope | 2 | 0 | 0 | 0 | 8 |
| Requirements & Semantics | 0 | 0 | 0 | 0 | 10 |
| Interfaces & Integration | 0 | 1 | 0 | 0 | 9 |
| Implementation & Configuration | 1 | 0 | 0 | 0 | 9 |
| Security, Trust & Isolation | 0 | 2 | 0 | 0 | 8 |
| Resilience & Failure Handling | 0 | 0 | 0 | 1 | 9 |
| Performance & Resource Efficiency | 2 | 0 | 0 | 2 | 6 |
| Observability & Explainability | 1 | 0 | 0 | 0 | 9 |
| Testing & Certification | 2 | 1 | 0 | 0 | 7 |
| Operations, Release & Governance | 3 | 0 | 0 | 0 | 7 |
