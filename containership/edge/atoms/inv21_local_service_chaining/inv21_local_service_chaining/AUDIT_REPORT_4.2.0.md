# INV-21 Local Service Chaining — Post-Hardening Audit

**Audited release:** 4.2.0  
**Audit date:** 2026-09-23  
**Scope:** supplied standalone archive after code hardening in this session.

## Verification summary

- Python compilation: PASS.
- Standalone runtime suite: **8/8 PASS**.
- Original pk_core conformance suite: **3/3 SKIPPED** because `pk_core` is not included/declared in this archive.
- Version consistency: `VERSION`, `__version__`, README and tests updated to **4.2.0**.
- Production gate: **NOT independently verifiable** from this standalone repository.

## Hardening completed in 4.2.0

- Synchronized, revisioned residency authority with immutable placement records and atomic unplacement.
- Per-hop capability policy hook plus explicit refusal telemetry.
- Injectable remote dispatch handoff.
- Stable error codes/details for local-chain refusal classes.
- Bounded trace and structured routing-decision telemetry.
- Stronger validation for host/callee/tenant/trace/path/depth/callback/telemetry configuration.
- Standalone runtime tests that execute even when `pk_core` is unavailable.

## Missing or incomplete production components (42)

### GAP-001 — Framework dependency packaging
**Severity:** CRITICAL  
**Checklist:** INV-21-C030, INV-21-C090, INV-21-C100

`pk_core` is required by normal imports and conformance/gate execution but is not bundled or declared in a package/dependency manifest; the framework test suite therefore skips in this isolated archive.

**Required completion:** Add pyproject.toml/lock or workspace manifest with a pinned pk_core source/version; make CI fail if pk_core conformance cannot execute.

### GAP-002 — Python package/release metadata
**Severity:** HIGH  
**Checklist:** INV-21-C016, INV-21-C031, INV-21-C040, INV-21-C093

No pyproject.toml/setup metadata, Python compatibility declaration, dependency constraints, build backend, wheel/sdist path, or reproducible environment lock.

**Required completion:** Add PEP 517 metadata, supported Python range, pinned dependencies/hashes, reproducible build and install smoke tests.

### GAP-003 — Versioned typed interface schemas
**Severity:** CRITICAL  
**Checklist:** INV-21-C021, INV-21-C022, INV-21-C026, INV-21-C082

PK_LOCAL_CHAIN/1, PK_RESIDENCY/1, and PK_CHAIN_DEPTH/1 are named in prose but have no machine-readable schema/WIT/IDL definitions or schema conformance tests.

**Required completion:** Add versioned schema files for requests, responses, errors, residency records and depth context; test backward/forward compatibility.

### GAP-004 — Authoritative capability-provider integration
**Severity:** CRITICAL  
**Checklist:** INV-21-C024, INV-21-C042, INV-21-C048

4.2 adds a per-hop capability hook, but no authoritative policy/capability provider is wired, versioned, or failover-tested. The compatibility fallback is not equivalent to external capability policy.

**Required completion:** Define the capability decision contract, inject the system authority in production, specify fail-closed outage behavior, and add integration/security tests.

### GAP-005 — Authentication and caller identity model
**Severity:** CRITICAL  
**Checklist:** INV-21-C023, INV-21-C044, INV-21-C048

Tenant and trace identifiers are caller-supplied strings; there is no authenticated principal, attestation, credential binding, or identity provenance on a local hop.

**Required completion:** Introduce authenticated call context derived from trusted runtime identity, not request-controlled strings; define attestation/outage semantics.

### GAP-006 — Production remote-transport adapter
**Severity:** HIGH  
**Checklist:** INV-21-C018, INV-21-C021, INV-21-C030, INV-21-C055, INV-21-C056

4.2 can inject `remote_dispatch`, but no concrete adapter to the repository's network transport exists and default behavior still returns a compatibility sentinel tuple.

**Required completion:** Implement/test the adjacent transport adapter, network-unavailable behavior, deadlines, error mapping, and semantic parity with local calls.

### GAP-007 — Async/await chaining path
**Severity:** HIGH  
**Checklist:** INV-21-C011, INV-21-C021, INV-21-C025, INV-21-C030

The contract depends on INV-16 Async component functions, but `Chainer.call()` and handlers are synchronous and do not await async handlers or remote dispatchers.

**Required completion:** Add `call_async`/async handler support with cancellation and context propagation; define sync/async interop and tests.

### GAP-008 — Deadlines, cancellation, retry, idempotency and backpressure
**Severity:** CRITICAL  
**Checklist:** INV-21-C025, INV-21-C053, INV-21-C054, INV-21-C067

No deadline/cancellation token, bounded retry policy, idempotency key semantics, queue/backpressure mechanism, or retry safety classification exists.

**Required completion:** Define hop deadline/cancellation propagation, idempotency metadata, retry policy with backoff/jitter, and bounded queues/admission.

### GAP-009 — Admission control and circuit breaking
**Severity:** HIGH  
**Checklist:** INV-21-C017, INV-21-C054, INV-21-C067, INV-21-C069

Depth and telemetry are bounded, but concurrent calls, per-tenant quotas, fan-out, handler saturation and remote failures have no admission/load-shedding/circuit-breaker controls.

**Required completion:** Add configurable concurrency/tenant limits, saturation signals, load shedding and circuit breaker state with deterministic tests.

### GAP-010 — Residency freshness/lease/watch protocol
**Severity:** CRITICAL  
**Checklist:** INV-21-C004, INV-21-C037, INV-21-C051, INV-21-C058

Residency is authoritative but has no TTL/lease, epoch/source provenance, watcher synchronization, stale-entry detection, duplicate-owner arbitration, or reconciliation protocol.

**Required completion:** Add generation/lease metadata, atomic snapshots, stale detection, ownership rules and reconciliation tests against the placement/control plane.

### GAP-011 — Lifecycle and state-transition model
**Severity:** MEDIUM  
**Checklist:** INV-21-C014, INV-21-C015, INV-21-C057

No explicit initializing/ready/degraded/quarantined/stopped lifecycle or legal transition table exists for the chainer/residency state.

**Required completion:** Define states, transition guards, restart/recovery semantics and machine-verifiable transition tests.

### GAP-012 — Declarative configuration schema
**Severity:** HIGH  
**Checklist:** INV-21-C033, INV-21-C034, INV-21-C035

Runtime knobs exist only as constructor arguments; there is no declarative config schema for depth, telemetry, policy provider, transport, quotas, or site/environment overrides.

**Required completion:** Add versioned config schema with secure defaults, validation, environment overlays and activation tests.

### GAP-013 — Configuration provenance and atomic activation
**Severity:** HIGH  
**Checklist:** INV-21-C036, INV-21-C037, INV-21-C038

No author/source/version/activation timestamp is recorded for configuration, and there is no transactional config activation or rollback snapshot.

**Required completion:** Add immutable config revisions, provenance, validate-before-swap activation and previous-revision rollback.

### GAP-014 — Ownership, escalation and ADR artifacts
**Severity:** MEDIUM  
**Checklist:** INV-21-C009, INV-21-C010, INV-21-C097

No CODEOWNERS/owner record, escalation path, architecture decision record, or incident contact metadata is present.

**Required completion:** Add OWNER/CODEOWNERS, ADR for direct composition/local fallback policy, and escalation/runbook ownership.

### GAP-015 — Requirements traceability matrix
**Severity:** HIGH  
**Checklist:** INV-21-C020, INV-21-C090, INV-21-C100

The 100-item checklist and master prompts exist, but there is no persisted matrix mapping each item to code/config/test/evidence and release acceptance status.

**Required completion:** Add machine-readable traceability matrix with evidence paths/hashes and gate status per C001-C100.

### GAP-016 — Supported-version compatibility matrix
**Severity:** HIGH  
**Checklist:** INV-21-C016, INV-21-C027, INV-21-C093

No matrix states supported local-chain schema versions, pk_core version, Python versions, adjacent component versions or downgrade behavior.

**Required completion:** Add compatibility matrix and automated N/N-1 (and documented N+1 where relevant) tests.

### GAP-017 — Artifact provenance, SBOM and signature verification
**Severity:** CRITICAL  
**Checklist:** INV-21-C045, INV-21-C094

No SBOM, dependency hashes, provenance attestation, signed release manifest, artifact digest verification, or vulnerability scan policy exists.

**Required completion:** Generate SBOM/provenance, pin hashes, sign release artifacts, verify on bootstrap, and define vulnerability response SLAs.

### GAP-018 — Tamper-evident security audit stream
**Severity:** CRITICAL  
**Checklist:** INV-21-C049, INV-21-C073, INV-21-C078

`DecisionEvent` is bounded in-process telemetry only; it is mutable runtime state, not a tamper-evident durable audit trail correlated with release/infrastructure lineage.

**Required completion:** Export security-sensitive decisions to an append-only signed/chained audit sink with stable IDs and release/topology correlation.

### GAP-019 — Telemetry export, health/readiness and dependency status
**Severity:** HIGH  
**Checklist:** INV-21-C071, INV-21-C072, INV-21-C073

Counters and decision records are in-memory only; there is no health/readiness surface, metrics exporter, structured log sink, dependency status, active capability report, or resource telemetry.

**Required completion:** Add health/readiness snapshot and OpenTelemetry/metrics/log adapters with stable labels and bounded cardinality.

### GAP-020 — Telemetry privacy, retention, sampling and explain view
**Severity:** MEDIUM  
**Checklist:** INV-21-C075, INV-21-C076, INV-21-C077, INV-21-C079

Decision reasons are recorded, but no privacy/redaction policy, retention/sampling/export rules, or operator-facing explain view exists.

**Required completion:** Define redaction/cardinality policy, retention/sampling configuration, and an explain API/view linking decisions to policy/topology inputs.

### GAP-021 — Dashboards and alerting
**Severity:** MEDIUM  
**Checklist:** INV-21-C080

No dashboards, SLO alerts, policy-rejection alerts, saturation alerts, dependency-failure alerts, or attack/defect discrimination rules are included.

**Required completion:** Add dashboard/alert definitions with tested thresholds and runbook links.

### GAP-022 — Reproducible benchmark suite and performance evidence
**Severity:** HIGH  
**Checklist:** INV-21-C061, INV-21-C062, INV-21-C063, INV-21-C064, INV-21-C068, INV-21-C070

The README states a p99 <20us SLO, but there are no benchmark harnesses, baseline artifacts, percentile distributions, overload/recovery runs, tenant overhead, power/thermal measurements, or regression gate.

**Required completion:** Add reproducible micro/macro benchmarks, p50/p95/p99/worst thresholds, edge power runs, and CI regression gates.

### GAP-023 — Capacity model and saturation signals
**Severity:** HIGH  
**Checklist:** INV-21-C017, INV-21-C067, INV-21-C069

No capacity formula/model covers concurrent chains, handler fan-out, per-tenant fairness, remote handoff pressure, CPU/memory limits, or saturation thresholds.

**Required completion:** Document and implement capacity ceilings, fairness rules, saturation metrics and sizing tests.

### GAP-024 — Serialization/zero-copy measurement evidence
**Severity:** MEDIUM  
**Checklist:** INV-21-C065, INV-21-C066

Direct handler composition avoids a network hop, but the repository does not measure serialization/copy/context-switch savings or prove zero-copy safety/semantics.

**Required completion:** Add comparative local-vs-remote profiling and correctness tests for any zero-copy/argument-handoff optimization.

### GAP-025 — Fuzz/property tests for untrusted inputs
**Severity:** HIGH  
**Checklist:** INV-21-C085

No fuzzing/property tests cover callee/tenant/trace/path values, handler failures, policy decisions, schema boundaries, or hostile oversized inputs.

**Required completion:** Add Hypothesis/Atheris or equivalent fuzz/property suite with corpus and CI budget.

### GAP-026 — Concurrency/race test suite
**Severity:** HIGH  
**Checklist:** INV-21-C086

Residency was made thread-safe, but there are no race tests for concurrent place/unplace/resolve/call, revision monotonicity, or policy/transport callback concurrency.

**Required completion:** Add multi-thread stress/race tests and, where supported, sanitizer/instrumented runs.

### GAP-027 — Threat-model-derived adversarial tests
**Severity:** CRITICAL  
**Checklist:** INV-21-C041, INV-21-C050, INV-21-C087

Current tests cover cross-tenant and capability refusal only; no replay/spoofing/injection/resource-exhaustion/side-channel/provider-compromise scenarios are exercised.

**Required completion:** Create threat model artifact and automated negative tests for each abuse case, including spoofed identity/trace, handler exceptions and exhaustion.

### GAP-028 — Adjacent-layer integration tests
**Severity:** CRITICAL  
**Checklist:** INV-21-C030, INV-21-C083

No executable integration suite proves interoperability with INV-20, INV-10, INV-16, INV-13 or SCH-01; the pk_core conformance test skips when the framework is absent.

**Required completion:** Create workspace integration fixtures for each declared dependency and make skipped mandatory integration tests a CI failure.

### GAP-029 — Platform/runtime compatibility tests
**Severity:** MEDIUM  
**Checklist:** INV-21-C084

No test matrix covers supported Python versions, CPU architectures, operating systems/runtimes, protocol versions or execution tiers.

**Required completion:** Declare supported matrix and run CI on representative Windows/Linux and target architectures/runtimes.

### GAP-030 — Fault-injection, partition and reconnect testing
**Severity:** HIGH  
**Checklist:** INV-21-C051, INV-21-C060, INV-21-C089

No tests inject handler crash/stall, policy-provider outage, stale residency, remote transport failure, node/site partition, reconnect, or degraded control plane.

**Required completion:** Add deterministic failure injection and recovery objective assertions.

### GAP-031 — Health/stall detection and quarantine control
**Severity:** HIGH  
**Checklist:** INV-21-C052, INV-21-C059

No handler stall thresholds, watchdogs, unhealthy placement suppression, quarantine/freeze control, or runtime emergency-disable switch exists.

**Required completion:** Add deadline/stall detection, quarantine state, disable switch and operator recovery path.

### GAP-032 — Crash consistency / restart / reconstruction procedure
**Severity:** MEDIUM  
**Checklist:** INV-21-C057, INV-21-C095

Residency state is memory-only with no explicit reconstruction source, startup reconciliation, snapshot/restore boundary, or restart invariant tests.

**Required completion:** Document authoritative reconstruction from placement source and test clean restart/reconciliation; explicitly mark backup N/A if derived state.

### GAP-033 — Canary/staged rollout and automated rollback
**Severity:** MEDIUM  
**Checklist:** INV-21-C038, INV-21-C092

README mentions rerunning gates and removing a registry component, but no canary/staged rollout mechanism, rollback automation, rollback criteria, or versioned migration procedure is supplied.

**Required completion:** Add rollout/rollback runbook and automation hooks with health/SLO abort criteria.

### GAP-034 — Patching, vulnerability and EOL policy
**Severity:** MEDIUM  
**Checklist:** INV-21-C094

No supported-version lifecycle, security patch SLA, CVE intake process, EOL timeline, or dependency update policy exists.

**Required completion:** Add SECURITY.md/support policy with response targets and release lifecycle.

### GAP-035 — Incident severity and response runbook
**Severity:** MEDIUM  
**Checklist:** INV-21-C097

No severity taxonomy, paging triggers, containment steps, evidence collection, recovery validation, or escalation workflow exists.

**Required completion:** Add incident runbook tied to local-chain failure/security signals.

### GAP-036 — Recurring review and exception/waiver registry
**Severity:** MEDIUM  
**Checklist:** INV-21-C098, INV-21-C099

No scheduled architecture/access/policy/dependency review record or owned exception/waiver/technical-debt registry with expiry exists.

**Required completion:** Add review cadence/checklist and machine-readable waiver/debt ledger with owner and expiry.

### GAP-037 — Formal production exit evidence bundle
**Severity:** CRITICAL  
**Checklist:** INV-21-C090, INV-21-C100

No generated evidence ledger/gate result is present in the archive, and normal gate execution cannot run without pk_core. Therefore production exit cannot be independently verified from this repository alone.

**Required completion:** Bundle signed machine-readable gate results, evidence ledger, hashes and release manifest produced in CI with all mandatory checks non-skipped.

### GAP-038 — Continuous integration workflow
**Severity:** HIGH  
**Checklist:** INV-21-C070, INV-21-C081, INV-21-C082, INV-21-C090

No CI configuration runs compile, runtime tests, full pk_core conformance, security checks, compatibility tests, benchmarks or packaging validation on change.

**Required completion:** Add CI pipeline with fail-on-skip mandatory gates, test artifacts and release evidence.

### GAP-039 — License and notice files
**Severity:** LOW  
**Checklist:** INV-21-C031, INV-21-C094

The archive contains no LICENSE/NOTICE file or explicit redistribution terms for the implementation package.

**Required completion:** Add the project-approved license and notice/provenance metadata.

### GAP-040 — Structured request/call context
**Severity:** HIGH  
**Checklist:** INV-21-C023, INV-21-C024, INV-21-C026, INV-21-C073

Caller identity, tenant, trace, deadline, capabilities and operation metadata are separate primitive arguments rather than a validated/versioned context object, increasing spoofing and compatibility risk.

**Required completion:** Define immutable typed CallContext with authenticated principal, tenant, trace/span, deadline, idempotency and capability claims/proofs.

### GAP-041 — Handler exception and failure-code normalization
**Severity:** HIGH  
**Checklist:** INV-21-C014, INV-21-C026, INV-21-C051

Chain-internal refusal errors are structured, but arbitrary local handler exceptions and remote adapter failures pass through without a stable error taxonomy or local/remote semantic normalization.

**Required completion:** Define error envelope/mapping rules and parity tests across local and remote paths.

### GAP-042 — Semantic-equivalence test suite
**Severity:** CRITICAL  
**Checklist:** INV-21-C011, INV-21-C013, INV-21-C029, INV-21-C082

The core promise that local and remote calls are semantically identical is asserted in prose but not tested against the same request corpus, errors, cancellation, authz, serialization and edge cases.

**Required completion:** Build a shared conformance corpus executed through both local and remote paths and byte/semantic-compare outcomes.

## Release conclusion

4.2.0 is materially safer and more testable than 4.1.0, but the standalone archive is **not a complete production-certification package**. The most important unresolved blockers are the absent/pinned `pk_core` integration, authenticated identity/capability authority, typed schemas, async/cancellation/backpressure semantics, authoritative residency freshness protocol, adjacent-layer integration tests, threat-derived security testing, performance evidence, and signed machine-readable exit-gate evidence.
