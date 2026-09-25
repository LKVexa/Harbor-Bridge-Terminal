# INV-61 Distributed WIT RPC — Post-Update Audit

> **Historical (4.2.0).** This audit is the input to the 4.3.0 pass. For the current status of M01–M32 see `CHECKLIST_EXECUTION_REPORT.md`, `TRACEABILITY.json` and `evidence/EXIT_GATE.json`.

**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** supplied archive only; no network access and no external `pk_core` installation was assumed.

## Executive result

The repository was parsed, statically checked, hardened, version-bumped, and re-tested. The dependency-free RPC primitive now passes its standalone test suite under normal and optimized (`python -O`) execution. Python compilation and checklist JSON parsing also pass.

The repository is **not yet a complete production distributed WIT RPC implementation**. It contains an in-process reference frame/dispatcher plus an external `pk_core` inventory/gating integration. The production components below are absent or incomplete in the supplied archive.

## Changes made in 4.2.0

- Extracted protocol behavior to `rpc.py`, removing the testability dependency on `pk_core`.
- Added fail-closed frame shape validation and exact field-set enforcement.
- Added non-empty identifier checks and hexadecimal fingerprint validation.
- Added a 256-argument ceiling.
- Rejected booleans, NaN, and infinity as deadlines or clocks.
- Enforced deadline expiry at `now >= deadline`.
- Added explicit interface and exact-version mismatch errors before dispatch.
- Preserved signature-drift protection and made signature serialization canonical.
- Added export validation and duplicate export rejection.
- Removed exception-class disclosure from callee trap responses.
- Added structured receiver counters.
- Added 11 dependency-free protocol tests.
- Removed the inaccurate README statement that `MASTER.md` exists.
- Bumped all local version pins from 4.1.0 to 4.2.0.

## Verification performed

| Check | Result |
|---|---|
| `CHECKLIST.json` JSON parse | PASS |
| Python compileall | PASS |
| Standalone protocol tests | PASS — 11/11 |
| Standalone tests under `python -O` | PASS — 11/11 |
| Bare runtime `assert` scan | PASS — none found |
| Dynamic execution/process scan | No production `eval`, `exec`, `pickle`, shell execution, or process spawning found |
| Original `pk_core` conformance tests | NOT EXECUTED — 3 skipped because `pk_core` is absent |

The skipped `pk_core` tests are an unresolved verification gap, not a successful gate.

## Missing or incomplete production components

### M01 — `pk_core` dependency and reproducible dependency manifest
**Related checklist:** C031, C040, C090, C100  
The package imports `pk_core` for its inventory contract and 100-item assessment, but the supplied archive contains no vendored dependency, package manifest, lock file, install metadata, or pinned external version. Therefore the original conformance/gate path cannot be reproduced from this archive alone.

### M02 — Missing historical master-source artifact (`MASTER.md`)
**Related checklist:** C020, C090, C100  
The previous README claimed the 100 per-item master prompt/workflow documents were carried in `MASTER.md`; that file is absent. The false claim was removed, but the source artifact itself remains missing.

### M03 — Real cross-host network transport adapter
**Related checklist:** C011, C012, C021, C030, C083  
`rpc.py` dispatches an already-materialized Python dictionary in-process. There is no socket/QUIC/HTTP/NATS/etc. transport binding, peer connection lifecycle, multiplexing, or remote invocation path proving operation across machines.

### M04 — WIT parser/bindings and canonical wire serialization
**Related checklist:** C021, C022, C029, C084, C085  
There is no WIT parser, generated binding layer, component-model value codec, canonical ABI mapping, byte-level frame codec, schema file, or interoperability fixture with an independent implementation.

### M05 — Protocol negotiation and supported-version compatibility matrix
**Related checklist:** C016, C027, C093  
4.2.0 safely rejects any exact version mismatch, but there is no negotiation protocol, compatibility range, downgrade policy, migration adapter, or machine-readable matrix of supported peer versions.

### M06 — Peer/node/workload authentication integration
**Related checklist:** C023, C044, C048  
No identity token, certificate, SPIFFE/SPIRE identity, attestation result, or authenticated peer context is consumed by `Endpoint.handle`.

### M07 — Authorization and capability enforcement
**Related checklist:** C024, C042, C043, C046  
No per-interface/function capability check, tenant/workload authorization policy, least-privilege grant, or denial audit path exists before dispatch.

### M08 — Transport encryption and key lifecycle
**Related checklist:** C047, C048  
Encryption is explicitly outside this component's current implementation and there is no concrete secure-channel integration, certificate rotation behavior, key outage behavior, or at-rest protection for any queued state.

### M09 — Replay/spoofing defenses and request identity
**Related checklist:** C041, C049, C050  
Frames do not carry request IDs, authenticated sender identity, nonce/sequence data, or replay windows. This prevents robust duplicate detection, spoofing attribution, and tamper-evident per-call audit correlation.

### M10 — Cancellation, idempotency, retry, and reconnect semantics
**Related checklist:** C014, C018, C025, C053, C057, C089  
Only an absolute deadline is implemented. There is no cancellation propagation, idempotency key, retry classification, bounded exponential backoff/jitter implementation, resume behavior, or reconnect state machine.

### M11 — Backpressure, admission control, and circuit breaking
**Related checklist:** C017, C025, C028, C054, C067  
A fixed argument-count ceiling now exists, but there are no byte-size limits, connection/concurrency ceilings, queues, per-tenant quotas, load shedding, token buckets, circuit breakers, or fairness controls.

### M12 — Configuration subsystem and provenance
**Related checklist:** C032-C040  
No declarative runtime configuration model, validation schema, immutable/mutable separation, site/environment overlays, provenance record, atomic activation, rollback transaction, or credential-separation mechanism is supplied.

### M13 — Tamper-evident security audit event pipeline
**Related checklist:** C049  
Internal counters are not an audit ledger. There is no signed/chained append-only record for authentication failures, authorization denials, version drift, signature mismatch, configuration change, or emergency disable activity.

### M14 — Health/readiness/dependency status endpoint
**Related checklist:** C052, C071  
No readiness state, dependency health model, stall detector, heartbeat, liveness endpoint, or version/config/capability health document is exposed.

### M15 — Production metrics exporter
**Related checklist:** C061-C064, C069, C072, C080  
`EndpointStats` records local counters only. There is no latency histogram, saturation/backlog/resource telemetry, Prometheus/OpenTelemetry exporter, cardinality policy, dashboard, or alert definition.

### M16 — Structured operational logging
**Related checklist:** C073, C075, C076, C077  
There is no structured log schema carrying stable node, tenant, workload, component, operation, decision reason, or privacy/redaction policy.

### M17 — Distributed trace propagation
**Related checklist:** C074, C078  
Frames do not carry trace/span context and no OpenTelemetry or equivalent propagation integration exists.

### M18 — Telemetry retention/privacy/export policy
**Related checklist:** C075, C079  
No sampling, retention, redaction, tenant privacy, exporter allow-list, or high-cardinality handling policy is present.

### M19 — Failover, partition, split-brain, duplicate-execution controls
**Related checklist:** C051, C055-C060, C089  
There is no distributed ownership or failover layer, partition policy, split-brain prevention, duplicate execution suppression, quarantine/freeze control, or recovery objective implementation.

### M20 — Durable/restart/replay semantics for mutable state
**Related checklist:** C057, C058, C095  
The implementation keeps counters and registered functions only in memory. There is no checkpoint, reconstruction format, durable state policy, restart behavior, or backup/restore procedure. If the intended production service is fully stateless, that must be formally documented and tested instead.

### M21 — Requirements specification and traceability matrix
**Related checklist:** C011-C020  
`CHECKLIST.json` contains requirement prompts, and `contract.py` contains broad declarations, but there is no SHALL-level specification with unique implementation/evidence links for every requirement, no lifecycle/state model, no explicit failure taxonomy, and no precedence model for security/residency/SLO/cost conflicts.

### M22 — Owner, escalation path, and approved architecture decision record
**Related checklist:** C009, C010  
No accountable production owner, escalation contact/path, or ADR approving wRPC and its architectural tradeoffs is in the archive.

### M23 — Security architecture and adversarial test suite
**Related checklist:** C041-C050, C087  
The contract lists three threats, but there is no complete threat model, trust-boundary diagram, abuse-case catalog, privilege-escalation/injection/replay/spoofing/resource-exhaustion suite, or security acceptance evidence.

### M24 — Parser/protocol fuzzing and property tests
**Related checklist:** C085  
Hostile deterministic cases were added, but no coverage-guided fuzz target, corpus, property-based generator, crash minimization, or fuzz CI gate exists.

### M25 — Concurrency and race-condition tests
**Related checklist:** C086  
No multithreaded/async concurrent dispatch tests, registration-vs-dispatch race tests, shared-counter synchronization guarantees, or race detector/tooling evidence is included.

### M26 — Adjacent-layer integration tests
**Related checklist:** C030, C083  
No executable integration harness proves interoperability with INV-11 interface contracts, INV-60 application fabric, INV-65 capability providers, or INV-36 control transport.

### M27 — Cross-runtime / cross-architecture compatibility certification
**Related checklist:** C084, C093  
No matrix or CI evidence exists for supported Python runtimes, Wasm runtimes, CPU architectures, operating systems, execution tiers, or peer protocol versions.

### M28 — Performance, capacity, power, and regression certification
**Related checklist:** C061-C070, C088  
The contract states a p99 framing-overhead SLO, but there are no reproducible benchmarks, p50/p95/p99/worst-case data, burst/overload/scale tests, memory/network/copy analysis, capacity model, constrained-edge power measurements, or release regression thresholds.

### M29 — Fault-injection, soak, disaster, and degraded-control-plane tests
**Related checklist:** C060, C088, C089  
No chaos/fault injector, long-duration soak, site/network partition harness, reconnect campaign, dependency outage tests, or degraded-control-plane certification exists.

### M30 — Supply-chain provenance, artifact verification, and SBOM
**Related checklist:** C045, C090  
No SBOM, signed release manifest, checksums file, SLSA/in-toto provenance, artifact signature verification policy, dependency vulnerability scan evidence, or approved-version policy is present.

### M31 — Production packaging/bootstrap artifact
**Related checklist:** C031-C040  
There is no `pyproject.toml`/wheel build, container/component package, pinned bootstrap script, deployment manifest, service definition, or deterministic installation path from an empty node.

### M32 — Formal operations/release/governance package
**Related checklist:** C091-C100  
The README has a short day-0/day-1/day-2 paragraph, but no complete SLO support policy, canary/staged rollout procedure, rollback runbook, emergency-disable mechanism, vulnerability/EOL SLA, incident severity/paging process, recurring review cadence, exception/waiver register, technical-debt register, or formal production exit-gate artifact.

## Residual implementation observations

- The 64-bit truncated SHA-256 fingerprint is suitable as a compatibility/drift detector, **not** as a security signature. Authentication and integrity must come from a separate authenticated channel or signed envelope.
- Exact field-set rejection is intentionally fail-closed but makes additive protocol evolution incompatible unless a negotiated schema/version introduces new fields.
- `EndpointStats` is not synchronized for concurrent mutation; thread/async safety remains undefined until M25 is addressed.
- The endpoint accepts already-decoded Python values, so byte-level memory exhaustion and malicious serialization behavior are outside the current test surface.

## Release conclusion

Version 4.2.0 is a hardened **reference implementation** with executable standalone protocol tests. It should not be represented as a complete production cross-host wRPC service until the missing components above—especially transport, WIT serialization, identity/capabilities, resilience controls, observability, integration/security/performance certification, reproducible packaging, and the `pk_core` gate dependency—are implemented and verified.
