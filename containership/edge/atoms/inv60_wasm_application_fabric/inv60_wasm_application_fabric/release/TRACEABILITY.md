# Traceability (M15) — generated

Summary: {"m_effective": {"LOCALLY_VERIFIED": 50, "PARTIAL": 27, "BLOCKED": 9}, "c_production": {"LOCALLY_VERIFIED": 55, "PARTIAL": 29, "BLOCKED": 8, "CONTRACT_ONLY": 8}, "c_pk_core_satisfied": 100}

## M-items
| M | declared | effective | tests | blocker / waiver |
|---|---|---|---|---|
| M01 | PARTIAL | PARTIAL | test_governance.Docs:passed | MASTER.md restored verbatim from the owner's series (UC32 payload); approval state/owner sign-off not recorded (W-APPROVALS) |
| M02 | BLOCKED | BLOCKED | test_governance.Packaging:passed | project licence must be chosen by the owner; no SPDX id can be asserted on his behalf (W-M02) |
| M03 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Packaging:passed |   |
| M04 | PARTIAL | PARTIAL | test_governance.Packaging:passed | SBOM generated (zero third-party runtime deps); no vulnerability feed/attestation signing available offline (W-SUPPLY) |
| M05 | PARTIAL | PARTIAL | test_governance.CI:passed | CI definition + local runner exist and ran here; never executed on a hosted runner (W-CI) |
| M06 | BLOCKED | BLOCKED | test_governance.Ownership:passed | structure and gate check exist; named people, pager and backup contact are owner decisions (placeholders fail the gate) (W-OWNERS) |
| M07 | PARTIAL | PARTIAL | test_governance.Docs:passed | ADR written with status 'proposed'; approvers not recorded (W-APPROVALS) |
| M08 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Requirements:passed |   |
| M09 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.ResultModel:passed |   |
| M10 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.Lifecycle:passed |   |
| M11 | PARTIAL | PARTIAL | test_semantics.Negotiation:passed | policy + N/N-1 protocol pair tests; no prior released wire version exists to test against (W-APPROVALS) |
| M12 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.ResourceLimits:passed, test_resilience.Concurrency:passed |   |
| M13 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Membership:passed |   |
| M14 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Placement:passed |   |
| M15 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Traceability:passed |   |
| M16 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.Interfaces:passed |   |
| M17 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_security.Authentication:passed, test_security.Ed25519Vectors:passed |   |
| M18 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_security.Authorization:passed |   |
| M19 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Deadlines:passed, test_resilience.Retries:passed |   |
| M20 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.ResultModel:passed |   |
| M21 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.Negotiation:passed |   |
| M22 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.ResourceLimits:passed, test_semantics.Interfaces:passed |   |
| M23 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.Interfaces:passed |   |
| M24 | BLOCKED | BLOCKED | — | needs wasmCloud hosts + NATS + wadm + real providers in an ephemeral environment (W-M25) |
| M25 | PARTIAL | PARTIAL | test_config_observability.WasmExecution:passed | real WebAssembly executes (V8 via Node) behind the hardened control plane; the wasmCloud/NATS/wadm adapter fails closed (W-M25) |
| M26 | PARTIAL | PARTIAL | test_governance.Matrix:passed | matrix records tested combinations here; wasmCloud/NATS/wadm pins are 'untested' until W-M25 closes (W-M25) |
| M27 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Schema:passed |   |
| M28 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Overlays:passed |   |
| M29 | PARTIAL | PARTIAL | test_config_observability.Activation:passed | provenance fields enforced; cryptographic attestation of config revisions not wired (W-SUPPLY) |
| M30 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Activation:passed |   |
| M31 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Activation:passed |   |
| M32 | PARTIAL | PARTIAL | test_config_observability.Secrets:passed | reference type, ACL, TTL, rotation, zeroize, scanning done; no real Vault/KMS adapter (W-M25) |
| M33 | PARTIAL | PARTIAL | test_governance.Bootstrap:passed | deterministic, idempotent reference bootstrap with evidence; does not provision NATS/wasmCloud (W-M25) |
| M34 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.ThreatModel:passed |   |
| M35 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_security.ArtifactSigning:passed |   |
| M36 | PARTIAL | PARTIAL | test_security.Authentication:passed | identity, enrolment, clone detection and reference attestation done; no hardware (TPM/TEE) attestation (W-HW) |
| M37 | PARTIAL | PARTIAL | test_security.Authorization:passed, test_config_observability.WasmExecution:passed | tenant-scoped authz/grants/placement + import-free Wasm sandbox; no network/filesystem namespace enforcement (W-M25) |
| M38 | BLOCKED | BLOCKED | — | transport encryption and managed key rotation require the real NATS/TLS/KMS layer (W-M25) |
| M39 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_security.Authentication:passed, test_security.Authorization:passed, test_security.ArtifactSigning:passed, test_config_observability.Secrets:passed |   |
| M40 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Ledger:passed |   |
| M41 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_security.Adversarial:passed |   |
| M42 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Membership:passed |   |
| M43 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Retries:passed |   |
| M44 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Breaker:passed, test_semantics.ResourceLimits:passed |   |
| M45 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Placement:passed |   |
| M46 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.EmergencyControls:passed, test_resilience.Membership:passed |   |
| M47 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Durability:passed |   |
| M48 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Membership:passed |   |
| M49 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.EmergencyControls:passed |   |
| M50 | PARTIAL | PARTIAL | test_resilience.Chaos:passed | seeded in-process fault injection; no process/network-level chaos against a real lattice (W-M25) |
| M51 | PARTIAL | PARTIAL | test_governance.Bench:passed | reproducible in-process benchmark + baseline on this container; not representative hardware (W-PERF) |
| M52 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Bench:passed |   |
| M53 | PARTIAL | PARTIAL | test_governance.Bench:passed | copy/hop analysis for the reference path; real transport serialization unmeasured (W-PERF) |
| M54 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.ResourceLimits:passed, test_config_observability.Telemetry:passed |   |
| M55 | BLOCKED | BLOCKED | — | edge power/thermal needs physical hardware and instrumentation (W-HW) |
| M56 | PARTIAL | PARTIAL | test_governance.Bench:passed | saturation curve for the reference control plane only (W-PERF) |
| M57 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Bench:passed |   |
| M58 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed |   |
| M59 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed |   |
| M60 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed |   |
| M61 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed |   |
| M62 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed |   |
| M63 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed, test_resilience.Placement:passed |   |
| M64 | PARTIAL | PARTIAL | test_governance.Evidence:passed | release lineage (version, source digest, config digest) recorded; no infrastructure graph to correlate with (W-M25) |
| M65 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_config_observability.Telemetry:passed |   |
| M66 | PARTIAL | PARTIAL | test_config_observability.Telemetry:passed | rules/dashboards defined against emitted metric names; not deployed to a monitoring stack (W-M25) |
| M67 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_semantics.Interfaces:passed, test_semantics.ResultModel:passed |   |
| M68 | BLOCKED | BLOCKED | — | same environment as M24 (W-M25) |
| M69 | PARTIAL | PARTIAL | test_semantics.Negotiation:passed, test_semantics.Interfaces:passed | protocol pairs + Python/Node consumers; CPU/OS matrix and real providers untested (W-CI) |
| M70 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_fuzz.Fuzz:passed |   |
| M71 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_resilience.Concurrency:passed, test_resilience.ConcurrencyRegressions:passed |   |
| M72 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_security.Adversarial:passed, test_governance.ThreatModel:passed |   |
| M73 | BLOCKED | BLOCKED | — | soak/fleet-scale needs a fleet and hours of runtime (W-PERF) |
| M74 | PARTIAL | PARTIAL | test_resilience.Chaos:passed, test_resilience.Membership:passed | partition/reconnect in-process; no degraded real control plane (W-M25) |
| M75 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Evidence:passed |   |
| M76 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_component.ConformanceTest:passed |   |
| M77 | PARTIAL | PARTIAL | test_governance.Docs:passed | SLO measurement/burn-rate policy written; support hours and ownership are owner decisions (W-OWNERS) |
| M78 | PARTIAL | PARTIAL | test_governance.Docs:passed | staged rollout with abort thresholds written; never rehearsed (W-DRILLS) |
| M79 | PARTIAL | PARTIAL | test_governance.Matrix:passed | see M26 (W-M25) |
| M80 | BLOCKED | BLOCKED | — | patching/EOL SLA commitments are owner decisions (W-OWNERS) |
| M81 | PARTIAL | PARTIAL | test_resilience.Durability:passed | restore from snapshot+WAL is tested; no drill on real storage (W-DRILLS) |
| M82 | PARTIAL | PARTIAL | test_governance.Docs:passed | written, not rehearsed (W-DRILLS) |
| M83 | PARTIAL | PARTIAL | test_governance.Docs:passed | plan written; paging integration and named escalation are owner decisions (W-OWNERS) |
| M84 | PARTIAL | PARTIAL | test_governance.Governance:passed | cadence defined; no review has been held (W-APPROVALS) |
| M85 | LOCALLY_VERIFIED | LOCALLY_VERIFIED | test_governance.Governance:passed |   |
| M86 | BLOCKED | BLOCKED | test_governance.Evidence:passed | gate evaluates mechanically and returns NO_GO: waivers unapproved, no independent reviewer, blocked items (W-APPROVALS) |

## C001–C100
| check | dimension | pk_core | M-items | production status |
|---|---|---|---|---|
| INV-60-C001 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C002 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C003 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C004 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C005 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C006 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C007 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C008 | Architecture & Scope | satisfied | — | CONTRACT_ONLY |
| INV-60-C009 | Architecture & Scope | satisfied | M06 | BLOCKED |
| INV-60-C010 | Architecture & Scope | satisfied | M07 | PARTIAL |
| INV-60-C011 | Requirements & Semantics | satisfied | M08 | LOCALLY_VERIFIED |
| INV-60-C012 | Requirements & Semantics | satisfied | M08 | LOCALLY_VERIFIED |
| INV-60-C013 | Requirements & Semantics | satisfied | M08 | LOCALLY_VERIFIED |
| INV-60-C014 | Requirements & Semantics | satisfied | M09 | LOCALLY_VERIFIED |
| INV-60-C015 | Requirements & Semantics | satisfied | M10 | LOCALLY_VERIFIED |
| INV-60-C016 | Requirements & Semantics | satisfied | M11 | PARTIAL |
| INV-60-C017 | Requirements & Semantics | satisfied | M12 | LOCALLY_VERIFIED |
| INV-60-C018 | Requirements & Semantics | satisfied | M13 | LOCALLY_VERIFIED |
| INV-60-C019 | Requirements & Semantics | satisfied | M14 | LOCALLY_VERIFIED |
| INV-60-C020 | Requirements & Semantics | satisfied | M15 | LOCALLY_VERIFIED |
| INV-60-C021 | Interfaces & Integration | satisfied | M16 | LOCALLY_VERIFIED |
| INV-60-C022 | Interfaces & Integration | satisfied | M16 | LOCALLY_VERIFIED |
| INV-60-C023 | Interfaces & Integration | satisfied | M17 | LOCALLY_VERIFIED |
| INV-60-C024 | Interfaces & Integration | satisfied | M18 | LOCALLY_VERIFIED |
| INV-60-C025 | Interfaces & Integration | satisfied | M19 | LOCALLY_VERIFIED |
| INV-60-C026 | Interfaces & Integration | satisfied | M20 | LOCALLY_VERIFIED |
| INV-60-C027 | Interfaces & Integration | satisfied | M21 | LOCALLY_VERIFIED |
| INV-60-C028 | Interfaces & Integration | satisfied | M22 | LOCALLY_VERIFIED |
| INV-60-C029 | Interfaces & Integration | satisfied | M23 | LOCALLY_VERIFIED |
| INV-60-C030 | Interfaces & Integration | satisfied | M24 | BLOCKED |
| INV-60-C031 | Implementation & Configuration | satisfied | M25 M26 | PARTIAL |
| INV-60-C032 | Implementation & Configuration | satisfied | M26 | PARTIAL |
| INV-60-C033 | Implementation & Configuration | satisfied | M27 | LOCALLY_VERIFIED |
| INV-60-C034 | Implementation & Configuration | satisfied | M27 | LOCALLY_VERIFIED |
| INV-60-C035 | Implementation & Configuration | satisfied | M28 | LOCALLY_VERIFIED |
| INV-60-C036 | Implementation & Configuration | satisfied | M29 | PARTIAL |
| INV-60-C037 | Implementation & Configuration | satisfied | M30 | LOCALLY_VERIFIED |
| INV-60-C038 | Implementation & Configuration | satisfied | M31 | LOCALLY_VERIFIED |
| INV-60-C039 | Implementation & Configuration | satisfied | M32 | PARTIAL |
| INV-60-C040 | Implementation & Configuration | satisfied | M33 | PARTIAL |
| INV-60-C041 | Security, Trust & Isolation | satisfied | M34 | LOCALLY_VERIFIED |
| INV-60-C042 | Security, Trust & Isolation | satisfied | M37 | PARTIAL |
| INV-60-C043 | Security, Trust & Isolation | satisfied | M37 | PARTIAL |
| INV-60-C044 | Security, Trust & Isolation | satisfied | M36 | PARTIAL |
| INV-60-C045 | Security, Trust & Isolation | satisfied | M35 | LOCALLY_VERIFIED |
| INV-60-C046 | Security, Trust & Isolation | satisfied | M37 | PARTIAL |
| INV-60-C047 | Security, Trust & Isolation | satisfied | M38 | BLOCKED |
| INV-60-C048 | Security, Trust & Isolation | satisfied | M39 | LOCALLY_VERIFIED |
| INV-60-C049 | Security, Trust & Isolation | satisfied | M40 | LOCALLY_VERIFIED |
| INV-60-C050 | Security, Trust & Isolation | satisfied | M41 | LOCALLY_VERIFIED |
| INV-60-C051 | Resilience & Failure Handling | satisfied | M42 | LOCALLY_VERIFIED |
| INV-60-C052 | Resilience & Failure Handling | satisfied | M42 | LOCALLY_VERIFIED |
| INV-60-C053 | Resilience & Failure Handling | satisfied | M43 | LOCALLY_VERIFIED |
| INV-60-C054 | Resilience & Failure Handling | satisfied | M44 | LOCALLY_VERIFIED |
| INV-60-C055 | Resilience & Failure Handling | satisfied | M45 | LOCALLY_VERIFIED |
| INV-60-C056 | Resilience & Failure Handling | satisfied | M46 | LOCALLY_VERIFIED |
| INV-60-C057 | Resilience & Failure Handling | satisfied | M47 | LOCALLY_VERIFIED |
| INV-60-C058 | Resilience & Failure Handling | satisfied | M48 | LOCALLY_VERIFIED |
| INV-60-C059 | Resilience & Failure Handling | satisfied | M49 | LOCALLY_VERIFIED |
| INV-60-C060 | Resilience & Failure Handling | satisfied | M50 | PARTIAL |
| INV-60-C061 | Performance & Resource Efficiency | satisfied | M51 | PARTIAL |
| INV-60-C062 | Performance & Resource Efficiency | satisfied | M52 | LOCALLY_VERIFIED |
| INV-60-C063 | Performance & Resource Efficiency | satisfied | M51 | PARTIAL |
| INV-60-C064 | Performance & Resource Efficiency | satisfied | M51 | PARTIAL |
| INV-60-C065 | Performance & Resource Efficiency | satisfied | M53 | PARTIAL |
| INV-60-C066 | Performance & Resource Efficiency | satisfied | M53 | PARTIAL |
| INV-60-C067 | Performance & Resource Efficiency | satisfied | M54 | LOCALLY_VERIFIED |
| INV-60-C068 | Performance & Resource Efficiency | satisfied | M55 | BLOCKED |
| INV-60-C069 | Performance & Resource Efficiency | satisfied | M56 | PARTIAL |
| INV-60-C070 | Performance & Resource Efficiency | satisfied | M57 | LOCALLY_VERIFIED |
| INV-60-C071 | Observability & Explainability | satisfied | M58 | LOCALLY_VERIFIED |
| INV-60-C072 | Observability & Explainability | satisfied | M59 | LOCALLY_VERIFIED |
| INV-60-C073 | Observability & Explainability | satisfied | M60 | LOCALLY_VERIFIED |
| INV-60-C074 | Observability & Explainability | satisfied | M61 | LOCALLY_VERIFIED |
| INV-60-C075 | Observability & Explainability | satisfied | M62 | LOCALLY_VERIFIED |
| INV-60-C076 | Observability & Explainability | satisfied | M63 | LOCALLY_VERIFIED |
| INV-60-C077 | Observability & Explainability | satisfied | M63 | LOCALLY_VERIFIED |
| INV-60-C078 | Observability & Explainability | satisfied | M64 | PARTIAL |
| INV-60-C079 | Observability & Explainability | satisfied | M65 | LOCALLY_VERIFIED |
| INV-60-C080 | Observability & Explainability | satisfied | M66 | PARTIAL |
| INV-60-C081 | Testing & Certification | satisfied | M67 | LOCALLY_VERIFIED |
| INV-60-C082 | Testing & Certification | satisfied | M67 | LOCALLY_VERIFIED |
| INV-60-C083 | Testing & Certification | satisfied | M68 | BLOCKED |
| INV-60-C084 | Testing & Certification | satisfied | M69 | PARTIAL |
| INV-60-C085 | Testing & Certification | satisfied | M70 | LOCALLY_VERIFIED |
| INV-60-C086 | Testing & Certification | satisfied | M71 | LOCALLY_VERIFIED |
| INV-60-C087 | Testing & Certification | satisfied | M72 | LOCALLY_VERIFIED |
| INV-60-C088 | Testing & Certification | satisfied | M73 | BLOCKED |
| INV-60-C089 | Testing & Certification | satisfied | M74 | PARTIAL |
| INV-60-C090 | Testing & Certification | satisfied | M75 | LOCALLY_VERIFIED |
| INV-60-C091 | Operations, Release & Governance | satisfied | M77 | PARTIAL |
| INV-60-C092 | Operations, Release & Governance | satisfied | M78 | PARTIAL |
| INV-60-C093 | Operations, Release & Governance | satisfied | M79 | PARTIAL |
| INV-60-C094 | Operations, Release & Governance | satisfied | M80 | BLOCKED |
| INV-60-C095 | Operations, Release & Governance | satisfied | M81 | PARTIAL |
| INV-60-C096 | Operations, Release & Governance | satisfied | M82 | PARTIAL |
| INV-60-C097 | Operations, Release & Governance | satisfied | M83 | PARTIAL |
| INV-60-C098 | Operations, Release & Governance | satisfied | M84 | PARTIAL |
| INV-60-C099 | Operations, Release & Governance | satisfied | M85 | LOCALLY_VERIFIED |
| INV-60-C100 | Operations, Release & Governance | satisfied | M86 | BLOCKED |

## Problems
- none
