# PLN-03 v4.2.0 — Missing Components After Hardening

Static second-pass audit identified **56 distinct missing or incomplete production components** in the supplied standalone archive. Items are grouped as distinct remediation units; some map to multiple checklist checks. An adjacent estate repository may satisfy some dependencies, but no such evidence was present in this archive.

> Status meaning: these are not all code bugs. They include absent specifications, integration artifacts, operational controls, certification evidence, and unresolved architecture scope required by the repository's own 100-item checklist.

## Architecture & Scope

### MC-001 — Accountable production owner and escalation path
**Checklist:** C009

No owner, on-call group, escalation target, or RACI is present.

### MC-002 — Approved architecture decision record (ADR)
**Checklist:** C010

No ADR records the wasmCloud/wRPC/Wadm/Dapr-style technology choices, alternatives, or approval.

## Requirements & Semantics

### MC-003 — Normative SHALL-level requirements specification
**Checklist:** C011-C012

The checklist asks for requirements, but there is no normative requirements document covering cloud/datacenter/near-edge/far-edge behavior.

### MC-004 — Complete NFR specification
**Checklist:** C013

Only three SLO statements exist; durability, consistency, availability, isolation, determinism, and resource objectives are not specified comprehensively.

### MC-005 — Success/degraded/retryable/terminal outcome model
**Checklist:** C014

There is no state/error semantics document defining partial success, retryability, or terminal failures across APIs.

### MC-006 — Lifecycle state machine
**Checklist:** C015

No runtime/adapter lifecycle states or legal transition model exists.

### MC-007 — Compatibility and deprecation policy
**Checklist:** C016

No supported API/version compatibility, deprecation, or backward-compatibility policy exists.

### MC-008 — Quota and fairness model
**Checklist:** C017

The 1 MiB inline payload and transaction limits do not define tenant/workload quotas, scheduling fairness, or capacity ceilings.

### MC-009 — Disconnected/intermittent-network semantics
**Checklist:** C018

The contract names optional local-first adapters, but no reconnect, offline, replay, or reconciliation semantics are implemented or specified.

### MC-010 — Constraint precedence policy
**Checklist:** C019

No ordering is defined for conflicts among security, residency, SLO, and cost constraints.

### MC-011 — Requirements traceability matrix
**Checklist:** C020

No 100-item mapping connects requirement -> implementation -> test -> evidence artifact.

## Interfaces & Integration

### MC-012 — Versioned typed external schemas/WIT contracts
**Checklist:** C021-C022

PK_STATE/1, PK_MESSAGE/1, PK_SECRET/1, and PK_INVOKE/1 are names only; no WIT/IDL/JSON Schema/protobuf/OpenAPI definitions are packaged.

### MC-013 — Authentication and capability-token enforcement
**Checklist:** C023-C024

Static workload:capability bindings fail closed, but the mandatory absent/expired capability-token check in contract.py is not implemented.

### MC-014 — Timeout, cancellation, retry, and backpressure contract
**Checklist:** C025

No timeout/cancellation API, retry policy, backoff/jitter, or cross-plane backpressure protocol is implemented.

### MC-015 — Serializable machine-readable error envelope
**Checklist:** C026

Runtime exceptions now carry stable codes/details, but no wire/error schema, status mapping, or cross-language representation is defined.

### MC-016 — Mixed-version peer negotiation
**Checklist:** C027

No compatibility handshake or behavior for different supported peer versions exists.

### MC-017 — Complete interface resource-limit specification
**Checklist:** C028

Some local constants now bound payload/key/transaction sizes, but queue depth, connection, concurrency, request-rate, and tenant limits are not defined.

### MC-018 — Reference client/server examples and conformance fixtures
**Checklist:** C029

Unit tests exercise the Python reference runtime, but no external-interface fixtures or language-neutral examples are provided.

### MC-019 — Adjacent-layer integration test suite
**Checklist:** C030

PLN-02, INV-49, PLN-04, PLN-06, and PLN-07 are not exercised through automated end-to-end integration tests in this archive.

## Implementation & Configuration

### MC-020 — Pinned implementation/specification manifest
**Checklist:** C031

No manifest pins wasmCloud, wRPC, Wadm, Dapr-compatible specs, adapters, or adjacent-plane versions/digests.

### MC-021 — Declarative runtime configuration system
**Checklist:** C032-C035

There is no schema-backed config artifact separating immutable code from site/environment configuration with secure defaults and pre-activation validation.

### MC-022 — Configuration provenance ledger
**Checklist:** C036

No author, source, version, digest, activation time, or history is recorded for configuration.

### MC-023 — Atomic configuration update mechanism
**Checklist:** C037

The state adapter supports atomic state transactions, but runtime configuration itself has no transaction/commit mechanism.

### MC-024 — Configuration rollback mechanism
**Checklist:** C038

No automatic/operator-driven rollback implementation or revision store exists.

### MC-025 — Secret-safe configuration/diagnostic policy enforcement
**Checklist:** C039

Secrets are fetched separately, but there is no config/log redaction policy or automated leak test.

### MC-026 — Deterministic bootstrap/install path
**Checklist:** C040

No package manifest, dependency lock, bootstrap script, or reproducible empty-node installation procedure exists.

## Security, Trust & Isolation

### MC-027 — Full threat model artifact
**Checklist:** C041

contract.py lists five threats, but there is no threat model with trust boundaries, assets, abuse cases, mitigations, residual risk, and review ownership.

### MC-028 — Ambient-authority isolation implementation
**Checklist:** C043

Adapter isolation is delegated to PLN-04 when present; this archive contains no process/Wasm/microVM isolation enforcement.

### MC-029 — Node/peer/artifact/provider/control-plane authentication
**Checklist:** C044

No identity verification implementation exists.

### MC-030 — Artifact signature/digest/provenance verification
**Checklist:** C045

No signature, digest allowlist, SBOM attestation, or provenance validation is implemented.

### MC-031 — Complete tenant/workload isolation
**Checklist:** C046

Tenant key prefixing is tested, but execution, memory, network, device, and side-channel isolation are not implemented here.

### MC-032 — Encryption and managed key rotation
**Checklist:** C047

No transport encryption, at-rest encryption integration, KMS contract, or key-rotation mechanism is present.

### MC-033 — Identity/attestation/policy/key/time outage behavior
**Checklist:** C048

No fail-closed/fail-safe matrix or implementation covers these security dependencies.

### MC-034 — Tamper-evident security audit events
**Checklist:** C049

No append-only/hash-chained audit-event emitter exists for reads, writes, publishes, secret access, invocation, or denials.

### MC-035 — Comprehensive adversarial security tests
**Checklist:** C050

No fuzz/injection/spoofing/replay/escape/side-channel/resource-exhaustion campaign is packaged.

## Resilience & Failure Handling

### MC-036 — Failure catalog plus health/stall detectors
**Checklist:** C051-C052

A short failure_modes list exists, but no process/node/site/control-plane matrix, health probes, watchdog, or stall thresholds exist.

### MC-037 — Bounded retry with backoff/jitter
**Checklist:** C053

AdapterUnavailable is explicit, but the runtime does not implement safe retry classification, retry budgets, exponential backoff, or jitter.

### MC-038 — Full admission/load-shedding/circuit-breaker layer
**Checklist:** C054

Oversized inline messages are rejected, but rate/concurrency admission, circuit breakers, and dependency load shedding are absent.

### MC-039 — Residency/consistency-safe failover
**Checklist:** C055

No failover selection, fencing, or policy integration exists.

### MC-040 — Degraded operation mode
**Checklist:** C056

No automatic local-only/read-only/buffered/bulk-handoff degraded mode is implemented.

### MC-041 — Crash consistency, replay, fencing, and split-brain protection
**Checklist:** C057-C058

The in-memory adapter has no durable journal, restart/resume semantics, ownership epoch, lease, or fencing token.

### MC-042 — Quarantine/freeze/disable controls
**Checklist:** C059

No runtime kill switch, adapter quarantine, or policy-driven isolation API exists.

### MC-043 — Fault-injection recovery suite
**Checklist:** C060

No automated dependency/network/site failure injection tests are present.

## Performance & Resource Efficiency

### MC-044 — Performance engineering and release-regression suite
**Checklist:** C061-C070

No reproducible benchmarks, p50/p95/p99/worst-case thresholds, load/overload tests, overhead accounting, power measurements, capacity model, or performance release gate exists.

## Observability & Explainability

### MC-045 — Operational telemetry/explainability stack
**Checklist:** C071-C080

Signals are declared in contract.py, but no health/readiness endpoint, metrics emitter, structured logging, trace propagation, safe diagnostics, decision explanations, lineage correlation, retention policy, dashboard, or alerts are implemented.

## Testing & Certification

### MC-046 — Interface contract, compatibility, and fuzz testing
**Checklist:** C082-C085

Standalone unit tests now cover runtime behavior, but there are no schema-level contract tests, cross-version/architecture/provider compatibility tests, or fuzzers.

### MC-047 — Security, scale, soak, disaster, partition/reconnect test suites
**Checklist:** C087-C089

No comprehensive security-derived, benchmark/soak/fleet-scale, or disaster/network-partition certification suites are packaged.

### MC-048 — Captured machine-readable acceptance evidence
**Checklist:** C090

The README references pk_core evidence/gate commands, but pk_core and a resulting signed/sealed gate artifact are not packaged, so certification cannot be reproduced from this archive alone.

## Operations, Release & Governance

### MC-049 — Canary/staged rollout and emergency-disable implementation
**Checklist:** C092

README contains a brief rollback/disable note, but no canary criteria, staged promotion policy, automation, or tested rollback procedure is provided.

### MC-050 — Compatibility, vulnerability/EOL, and backup/restore governance
**Checklist:** C093-C095

No compatibility matrix, patch/vulnerability/EOL SLA, or backup/restore/migration/reconstruction procedure is packaged.

### MC-051 — Production operations/governance artifacts
**Checklist:** C096-C100

The README has a short day-0/day-1/day-2 outline, but no full runbooks, incident severity/paging plan, recurring review cadence, exception/waiver/debt registry, or captured formal production exit gate exists.

## Source-function coverage

### MC-052 — Actor and workflow service surface
**Checklist:** C010-C012

CHECKLIST.json names Dapr-style actor and workflow services in the source function, while contract.py explicitly omits durable workflow semantics and the runtime exposes no actor API. This architectural mismatch is unresolved.

### MC-053 — wasmCloud/wRPC/Wadm concrete integration
**Checklist:** C010-C012,C030

These technologies are named by the checklist, but no WIT packages, wRPC transport, wasmCloud host/provider integration, Wadm manifest, or interoperability test is present.

## Repository completeness

### MC-054 — MASTER.md master-prompt/workflow artifact
**Checklist:** n/a

The original README claimed MASTER.md was carried verbatim, but the uploaded archive does not contain it. The README now states the omission explicitly.

## Repository reproducibility

### MC-055 — pk_core dependency declaration/vendor bundle
**Checklist:** C031,C040,C090

component.py and contract.py require pk_core, but the archive contains neither pk_core nor a pyproject/requirements lock declaring a reproducible source/version.

## Repository supply chain

### MC-056 — License, SBOM, provenance, and CI policy artifacts
**Checklist:** C045,C094

No LICENSE/NOTICE, SBOM, build provenance/attestation, dependency scanning policy, or CI workflow is included in this component archive.


## 4.3.0 remediation status

See `REMEDIATION_STATUS.json` (per-finding status, artifacts, linked tests, open remainder) and `TRACEABILITY.json`.
