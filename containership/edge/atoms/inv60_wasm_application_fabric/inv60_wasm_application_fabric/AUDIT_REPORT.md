# INV-60 Wasm Application Fabric — Post-Hardening Audit

**Audited release:** 4.2.0  
**Audit date:** 2026-09-22  
**Input release:** 4.1.0  
**Scope:** supplied archive only; no assumptions are made about sibling repositories or services not included in the archive.

## Executive result

The supplied package is a compact **reference/conformance model**, not a complete production Wasm application fabric. The 4.2.0 pass repairs state-integrity and lifecycle defects in the reference runtime, separates dependency-free runtime logic from the `pk_core` conformance adapter, adds independent unit coverage, corrects an inaccurate README claim, and preserves fail-closed behavior around artifact digests and runtime links.

The dependency-free runtime test suite passes locally. The 100-item `pk_core` conformance suite is **not locally certifiable from this archive** because `pk_core` is an external dependency and is not included or installed in the audit environment. Its tests skip rather than execute when that dependency is absent. Accordingly, this audit does **not** repeat the prior “all 100 requirements satisfied” claim as a verified local result.

## Changes applied in 4.2.0

1. Added `runtime.py`, isolating the lattice model from `pk_core` so core safety behavior can be tested independently.
2. Added host-name, component-name, link-name, unique-membership, instance-placement, and failover-counter invariant validation.
3. Changed artifact ingestion to copy bytes-like input to immutable `bytes` before hashing/storage.
4. Added explicit rejection of duplicate component starts (`AlreadyRunning`) instead of silent placement overwrite.
5. Added `add_host()` membership lifecycle support.
6. Added `stop()` and `unlink()` lifecycle operations; stopping a component revokes its links.
7. Required components to be running before links can be granted and required providers to be callable.
8. Added a live-host check before routing a call.
9. Made `lose_host()` refusal transactional: survivor availability is checked before host/placement mutation.
10. Added dependency-free unit tests for digest integrity, unknown-artifact atomicity, failover atomicity, authority revocation, duplicate start, host membership, and input validation.
11. Corrected README metadata that previously said `MASTER.md` was carried in the archive even though it is absent.
12. Bumped `VERSION`, `__version__`, tests, README, and changelog from 4.1.0 to 4.2.0.

## Verification performed

- Python bytecode compilation: **PASS** for `__init__.py`, `contract.py`, `component.py`, `runtime.py`, `tests/test_component.py`, and `tests/test_runtime.py`.
- `tests/test_runtime.py`: **PASS**, 4 tests.
- Checklist JSON structural check: **PASS**, 100 items, 100 unique check IDs, ordinals 1–100.
- `tests/test_component.py`: **SKIPPED** in this environment because `pk_core` is unavailable; therefore the 100-requirement conformance result is **UNVERIFIED LOCALLY**.
- Optimized-mode (`python -O`) conformance: cannot be re-certified without `pk_core`; dependency-free runtime tests contain no production `assert`-dependent behavior.

# Complete post-update missing-component inventory

The list below records components required by the repository's own `CHECKLIST.json`, README claims, or stated production responsibility that are not implemented or evidenced in the supplied 4.2.0 repository. “Missing” means no concrete implementation/artifact exists in this archive; it does not assert that the component cannot exist in a separate repository.

## A. Source, packaging, ownership, and architecture

### M01 — `MASTER.md` source-series artifact
**Status:** Missing.  
The README/source-series metadata references a master prompt/workflow corpus, but no `MASTER.md` exists in the archive.

### M02 — License and notice artifacts
**Status:** Missing.  
No `LICENSE`, `NOTICE`, copyright policy, or explicit redistribution terms are present.

### M03 — Reproducible package/build metadata
**Status:** Missing.  
No `pyproject.toml`, build backend, package manifest, dependency declaration, lockfile, or reproducible environment specification is provided.

### M04 — Dependency/SBOM provenance
**Status:** Missing.  
No SBOM, dependency inventory, hashes, provenance attestation, or vulnerability-scanning policy is present.

### M05 — CI/release automation
**Status:** Missing.  
No CI workflow executes compilation, runtime tests, `pk_core` tests, optimized-mode tests, linting, security checks, packaging, or release gates.

### M06 — Accountable owner and escalation path (C009)
**Status:** Missing.  
No owner, service team, pager/escalation chain, or responsibility matrix is declared.

### M07 — Approved architecture decision record (C010)
**Status:** Missing.  
No ADR records why wasmCloud is selected, alternatives considered, constraints, consequences, or approval.

## B. Requirements and semantics

### M08 — Normative SHALL-level requirements specification (C011–C013)
**Status:** Missing.  
`CHECKLIST.json` asks for requirements, but the repository contains no normative, versioned SHALL-level product specification with measurable acceptance criteria across target environments.

### M09 — Formal result/failure semantics (C014)
**Status:** Missing.  
Success, partial success, degraded operation, retryable failure, and terminal failure are not modeled as a stable public state/error contract.

### M10 — Lifecycle state machine (C015)
**Status:** Partial/missing production artifact.  
The reference model now has start/stop/link/unlink operations, but there is no authoritative state machine, transition table, illegal-transition matrix, or distributed lifecycle protocol.

### M11 — Backward-compatibility/version policy (C016)
**Status:** Missing.  
No compatibility policy describes protocol evolution, deprecation, migration, or mixed-version behavior.

### M12 — Capacity, quota, and fairness model (C017)
**Status:** Missing.  
No tenant/workload quotas, placement ceilings, fairness algorithm, or enforcement exists.

### M13 — Network partition/offline semantics (C018)
**Status:** Missing.  
No behavior is defined or implemented for partitions, reconnect, isolated sites, stale membership, or offline provider access.

### M14 — Constraint precedence policy (C019)
**Status:** Missing.  
No deterministic precedence is defined for security, residency, SLO, availability, and cost conflicts.

### M15 — Requirements traceability matrix (C020)
**Status:** Missing.  
No machine-readable map connects each C001–C100 requirement to concrete source, test, operational evidence, and release evidence.

## C. Interfaces and integration

### M16 — Versioned WIT/RPC/API schemas (C021–C022)
**Status:** Missing.  
The strings `PK_LATTICE_START/1`, `PK_LATTICE_LINK/1`, and `PK_LATTICE_CALL/1` are descriptions, not typed schemas. No WIT files, protobuf/OpenAPI schemas, message definitions, or compatibility fixtures are present.

### M17 — Boundary authentication (C023)
**Status:** Missing.  
No host, workload, provider, peer, or control-plane authentication protocol is implemented.

### M18 — Boundary authorization/capability policy (C024)
**Status:** Partial.  
The reference model enforces presence of a local runtime link, but it has no principal identity, policy engine, capability token, tenant scope, or authorization decision record.

### M19 — Timeout/cancellation/retry/idempotency/backpressure contract (C025)
**Status:** Missing.  
Calls directly invoke Python providers and have no deadlines, cancellation, retry safety classification, idempotency keys, queueing, or backpressure.

### M20 — Structured machine-readable failure model (C026)
**Status:** Partial.  
Python exception classes exist, but there are no stable error codes, serialized details, retry hints, causal metadata, or protocol mapping.

### M21 — Mixed-version negotiation (C027)
**Status:** Missing.

### M22 — Interface resource limits (C028)
**Status:** Missing.  
No payload, concurrency, connection, queue, memory, or execution limits are defined/enforced.

### M23 — External conformance fixtures/examples (C029)
**Status:** Missing.  
Unit examples are not protocol conformance fixtures consumable by other implementations.

### M24 — Adjacent-layer integration suite (C030)
**Status:** Missing.  
No executable integration tests cover deployment manager, artifact provenance/signing, capability providers, component composition, or real transport.

## D. Production implementation and configuration

### M25 — Real wasmCloud fabric adapter/runtime (C031)
**Status:** Missing.  
The repository models behavior in Python but does not instantiate or manage wasmCloud hosts/components/providers, NATS, wadm, WIT interfaces, or a production lattice.

### M26 — Pinned supported implementation matrix (C031)
**Status:** Missing.  
No wasmCloud/NATS/wadm/WASI/Component Model versions or approved hashes are pinned.

### M27 — Declarative configuration schema and secure defaults (C033–C034)
**Status:** Missing.

### M28 — Site/environment overlays (C035)
**Status:** Missing.

### M29 — Configuration provenance/audit metadata (C036)
**Status:** Missing.

### M30 — Atomic distributed configuration activation (C037)
**Status:** Missing.  
Atomicity of the in-memory Python host-loss operation does not constitute a distributed configuration transaction.

### M31 — Configuration/deployment rollback controller (C038)
**Status:** Missing.

### M32 — Secret references/integration (C039)
**Status:** Missing.  
No secret-store contract, secret reference type, redaction path, or credential lifecycle exists.

### M33 — Deterministic empty-environment bootstrap automation (C040)
**Status:** Missing.  
README commands assume prerequisites rather than provisioning a healthy fabric from an empty environment.

## E. Security, trust, and isolation

### M34 — Formal threat model (C041)
**Status:** Missing.  
Three threat strings in `contract.py` are not a complete trust-boundary/data-flow threat model.

### M35 — Artifact signature/provenance verification (C045)
**Status:** Missing.  
Digest equality is enforced, but signatures, signer identity, provenance, policy approval, revocation, and trusted root verification are not.

### M36 — Node/peer/provider/control-plane identity and attestation (C044)
**Status:** Missing.

### M37 — Tenant/workload isolation enforcement (C042–C043, C046)
**Status:** Missing.  
No sandbox policy, namespace, network policy, filesystem/device restriction, secret boundary, or tenant-aware state partition exists in executable code.

### M38 — Encryption and managed key rotation (C047)
**Status:** Missing.

### M39 — Identity/policy/key/time dependency failure behavior (C048)
**Status:** Missing.

### M40 — Tamper-evident security audit ledger (C049)
**Status:** Missing locally.  
README references `pk_core` evidence, but no emitted evidence ledger or local implementation is included.

### M41 — Adversarial security test suite (C050)
**Status:** Missing.  
No privilege-escalation, injection, replay, spoofing, sandbox-escape, side-channel, or resource-exhaustion tests exist.

## F. Resilience and distributed failure handling

### M42 — Health/stall detection (C052)
**Status:** Missing.

### M43 — Bounded retry/backoff/jitter policy (C053)
**Status:** Missing.

### M44 — Admission control/load shedding/circuit breaking (C054)
**Status:** Missing.

### M45 — Residency/consistency-aware failover policy (C055)
**Status:** Missing.  
Current failover selects surviving hosts round-robin without placement constraints.

### M46 — Degraded-operation modes (C056)
**Status:** Missing.

### M47 — Durable state and crash/restart/replay semantics (C057)
**Status:** Missing.  
All reference runtime state is in-memory.

### M48 — Split-brain/lease/fencing/duplicate-execution protection (C058)
**Status:** Missing.

### M49 — Quarantine/freeze/emergency isolation controls (C059)
**Status:** Missing.

### M50 — Fault-injection/chaos recovery suite (C060)
**Status:** Missing.

## G. Performance and resource efficiency

### M51 — Reproducible benchmark suite and baselines (C061, C063–C064)
**Status:** Missing.

### M52 — Complete percentile/worst-case SLO thresholds (C062)
**Status:** Partial.  
A p99 routing-overhead target exists, but no p50/p95/worst-case targets or measured baseline are included.

### M53 — Serialization/copy/hop efficiency analysis (C065–C066)
**Status:** Missing.

### M54 — Bounded runtime resources (C067)
**Status:** Missing.  
Registry, instances, links, call fan-out, and provider execution are unbounded in the reference model.

### M55 — Edge power/thermal characterization (C068)
**Status:** Missing.

### M56 — Capacity/saturation model (C069)
**Status:** Missing.

### M57 — Performance-regression release gate (C070)
**Status:** Missing.

## H. Observability and explainability

### M58 — Health/readiness/version/config/dependency status endpoint (C071)
**Status:** Missing.

### M59 — Runtime metrics emitter (C072)
**Status:** Missing.  
Signal names in `contract.py` are declarations only; no metrics are emitted.

### M60 — Structured operational/security logging (C073)
**Status:** Missing.

### M61 — Distributed trace-context propagation (C074)
**Status:** Missing.

### M62 — Safe high-cardinality diagnostic interface (C075)
**Status:** Missing.

### M63 — Decision-reason/explainability record (C076–C077)
**Status:** Missing.

### M64 — Release-lineage/infrastructure-graph correlation (C078)
**Status:** Missing.

### M65 — Telemetry retention/sampling/privacy/export policy (C079)
**Status:** Missing.

### M66 — Dashboards and alert rules (C080)
**Status:** Missing.

## I. Testing and certification

### M67 — Public-interface contract tests (C082)
**Status:** Missing beyond direct Python unit behavior.

### M68 — Full adjacent-layer/execution-tier integration tests (C083)
**Status:** Missing.

### M69 — CPU/runtime/provider/protocol compatibility tests (C084)
**Status:** Missing.

### M70 — Fuzz/property tests for untrusted boundaries (C085)
**Status:** Missing.

### M71 — Concurrency/race/distributed-state tests (C086)
**Status:** Missing.

### M72 — Threat-model-derived security tests (C087)
**Status:** Missing.

### M73 — Benchmark/soak/burst/fleet-scale tests (C088)
**Status:** Missing.

### M74 — Disaster/partition/reconnect/degraded-control-plane tests (C089)
**Status:** Missing.

### M75 — Machine-readable release acceptance evidence bundled with release (C090)
**Status:** Missing.  
The archive contains no generated `evidence/` ledger or `conformance/PK_GATE_RESULTS.json`.

### M76 — Self-contained `pk_core` dependency or pinned acquisition mechanism
**Status:** Missing.  
The conformance suite requires `pk_core`, but the archive neither vendors it nor declares a reproducible pinned dependency source; tests skip when it is unavailable.

## J. Operations, release, and governance

### M77 — Complete SLO/support commitment artifact (C091)
**Status:** Partial.  
Three SLO statements exist, but no measurement method, window, alert threshold, support hours, ownership, or burn-rate policy is defined.

### M78 — Canary/staged rollout/rollback/emergency-disable runbook (C092)
**Status:** Partial.  
README gives high-level gate/rollback language but no executable rollout stages, success criteria, abort thresholds, or emergency procedure.

### M79 — Supported-version compatibility matrix (C093)
**Status:** Missing.

### M80 — Patching/vulnerability/EOL SLA (C094)
**Status:** Missing.

### M81 — Backup/restore/migration/reconstruction runbook (C095)
**Status:** Missing.

### M82 — Complete day-0/day-1/day-2 runbooks (C096)
**Status:** Partial.  
The README contains a short outline, not operational procedures with prerequisites, validation, failure paths, and recovery steps.

### M83 — Incident severity/paging/escalation/containment/recovery plan (C097)
**Status:** Missing.

### M84 — Recurring review control and evidence (C098)
**Status:** Missing.

### M85 — Exception/waiver/technical-debt/deprecation register (C099)
**Status:** Missing.

### M86 — Formal production exit-gate artifact (C100)
**Status:** Missing locally.  
No signed/dated gate result proving architecture, security, resilience, performance, observability, rollback, and ownership readiness is bundled.

## Final classification

**Reference-model code quality after 4.2.0:** materially improved and locally testable.  
**Production completeness:** incomplete.  
**Production certification:** not established by this archive.  
**Blocking reason:** the repository lacks the majority of production transport, identity/security, distributed-state, resilience, performance, telemetry, integration, certification, and operational-governance components enumerated above.


---

# 4.3.0 addendum — missing-components implementation pass (2026-09-22)

**Input:** 4.2.0 hardened archive + the M01–M86 implementation checklist. **Output:** 4.3.0.
Status vocabulary: LOCALLY_VERIFIED (implemented and exercised by passing tests here), PARTIAL, BLOCKED. Nothing is marked
COMPLETE: the checklist requires production-boundary evidence, an independent reviewer and a signed exit gate.

| | count | items |
|---|---|---|
| LOCALLY_VERIFIED | 50 | M03 M08 M09 M10 M12–M23 M27 M28 M30 M31 M34 M35 M39–M49 M52 M54 M57–M63 M65 M67 M70–M72 M75 M76 M85 |
| PARTIAL | 27 | M01 M04 M05 M07 M11 M25 M26 M29 M32 M33 M36 M37 M50 M51 M53 M56 M64 M66 M69 M74 M77–M79 M81–M84 |
| BLOCKED | 9 | M02 (licence choice) M06 (named owners) M24 M68 (real lattice integration) M38 (transport encryption/KMS) M55 (power/thermal hardware) M73 (soak/fleet) M80 (patch SLA) M86 (exit gate) |

**Verification performed:** `tools/ci.py --strict` — 194 tests passed / 0 failed / 0 skipped under `python`, same suite passes under
`python -O`; Node consumer validated 47 fixtures and executed `add.wasm`; pk_core W0–W9 workflow certified 100/100 with an intact
evidence chain (`release/pk_evidence.jsonl`); traceability 0 problems; benchmark regression clean.

**What pk_core's GO means:** the 100 checklist items are answered at contract/reference level. It is **not** the production gate.

**Production exit gate:** `release/EXIT_GATE.json` = **NO_GO** (tests, pk_core and traceability checks pass; ownership, independent
review, 36 non-verified items with only *proposed* waivers, and the absent production boundary block).

**Remaining work to reach GO** is listed per waiver in `WAIVERS.json`: provision the pinned wasmCloud/NATS/wadm lattice and implement
`WasmCloudBackend` + the M24/M68 integration suite (W-M25); owner decisions on licence, owners, SLAs (W-M02, W-OWNERS); independent
approvals (W-APPROVALS); hardware attestation and power/thermal (W-HW); representative-hardware benchmarks and soak (W-PERF); hosted CI
matrix (W-CI); signed SBOM/config attestations (W-SUPPLY); runbook drills (W-DRILLS).
