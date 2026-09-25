# INV-26 Updated Repository Audit Report

**Audited version:** 5.0.0  
**Audit date:** 2026-09-23

## Validation performed

- Safe ZIP extraction with path traversal rejection.
- Full Python AST parse and `compileall`: PASS.
- Standalone snapshot-domain tests: **10/10 PASS**.
- `pk_core` conformance suite: **3 SKIPPED** because `pk_core` is not included/importable in this repository artifact.
- Checklist cardinality: **100 items present**.

## Fixed in this pass

1. Full SHA-256 device-model fingerprint instead of a 16-hex-character truncation.
2. Strict device identifier validation, including rejection of strings-as-iterables and duplicate device IDs.
3. Tenant, workload, and environment restore binding.
4. Thread-safe duplicate capture and restore mutation.
5. Read-only external snapshot map.
6. Fresh 256-bit entropy material per successful restore with an injectable RNG integration hook.
7. Fail-closed behavior when entropy injection fails.
8. Non-secret entropy proof rather than returning seed material.
9. Finite, non-negative restore timing validation and monotonic measurement support.
10. Security-context fields included in canonical signed metadata.
11. Independent tests no longer all disappear when `pk_core` is absent.
12. Interface/version bump to 5.0.0 / PK_SNAPSHOT/2 / PK_SNAPSHOT_RESTORE/2.

## Missing components remaining after the update

The repository is now a stronger reference model, but it is **not yet a complete production implementation**. The following checklist-backed components are absent or not evidenced by repository artifacts.

### Architecture / governance
- **C009:** accountable owner and escalation path.
- **C010:** approved architecture decision record (ADR).
- **C020:** requirements-to-implementation-to-evidence traceability matrix.

### Requirements / semantics
- **C012:** explicit cloud/datacenter/near-edge/far-edge applicability matrix.
- **C014-C019:** formal success/degraded/failure semantics, lifecycle state machine, compatibility policy, quotas/fairness, disconnected-network semantics, and conflict-precedence policy.

### Interfaces / integration
- **C021-C029:** complete boundary inventory, machine-readable typed schema files, authentication/authorization requirements, timeout/cancellation/retry/idempotency/backpressure rules, stable machine-readable error-code catalog, mixed-version compatibility behavior, interface resource limits, and conformance fixtures/examples.
- **C030:** automated adjacent-layer integration tests.
- No concrete hypervisor adapter exists for Firecracker, Cloud Hypervisor, QEMU/KVM, or another production runtime.
- The default entropy injector validates seed delivery only; it does **not** write entropy into a real guest RNG device.
- No snapshot blob storage adapter exists by design, but no integration contract/port is supplied for one either.

### Implementation / configuration
- **C031-C040:** pinned production implementation/specification matrix, immutable artifact/config separation, declarative configuration format, config validation, site/environment overlays, config provenance, transactional activation, rollback mechanics, secret/config separation policy artifact, and deterministic bootstrap automation.
- No `pyproject.toml`/build metadata, dependency lock, reproducible build definition, or installable package manifest.

### Security / trust
- **C041-C045, C047-C050:** repository-local threat-model document, least-privilege capability model, ambient-authority elimination evidence, peer/node/artifact authentication design, mandatory signature/provenance enforcement, encryption-at-rest/in-transit design, dependency-outage trust behavior, tamper-evident security audit ledger, and adversarial security test suite.
- GAP-07 signing remains optional/external and is not included in this ZIP.
- No key-management/KMS integration, key rotation, attestation, anti-replay token, snapshot confidentiality layer, or secure erase lifecycle is implemented.

### Resilience
- **C051-C060:** comprehensive failure-mode matrix, health/stall thresholds, bounded retry policy, admission control/load shedding/circuit breaker, failover design, degraded mode, crash-consistency/replay semantics, split-brain/duplicate-execution protection, quarantine/disable controls, and fault-injection tests.
- State is process-memory only; restart reconstruction/persistence semantics are absent.

### Performance / resource efficiency
- **C061-C070:** reproducible benchmark harness, p50/p95/p99/worst-case thresholds beyond the single 10 ms budget, load/burst/overload/scale/recovery measurements, per-tenant/workload overhead accounting, copy/serialization profiling, optimization evidence, explicit concurrency/resource ceilings, edge power/thermal measurements, capacity model/saturation signals, and regression gate.
- The current `elapsed_ms` fixture is suitable for deterministic tests but is not a production benchmark.

### Observability
- **C071-C080:** health/readiness endpoint, structured metrics exporter, structured logs, trace propagation, privacy-safe high-cardinality diagnostics, decision-reason records, operator explain view, release/topology correlation, telemetry retention/sampling/export policy, dashboards, and alerts.
- Contract signal names exist, but no telemetry implementation exports them.

### Testing / certification
- **C082-C085, C087-C090:** public-interface contract tests, adjacent-layer integration tests, architecture/runtime/hypervisor compatibility matrix tests, fuzzing, threat-model-derived adversarial tests, benchmark/soak/burst/fleet tests, disaster/partition/degraded-control-plane tests, and machine-readable release acceptance evidence.
- **C086 is only partially covered:** duplicate-capture concurrency is tested; distributed races and restore/capture contention are not.
- The external `pk_core` dependency is absent, so the 100-item conformance/gate cannot be executed from this ZIP alone.

### Operations / release / governance
- **C091-C100:** full support commitments, staged/canary rollout procedure, compatibility matrix, vulnerability/EOL SLA, backup/reconstruction runbook, complete day-0/day-1/day-2 runbooks, incident severity/escalation procedures, recurring review schedule, exception/waiver/debt register, and formal production exit-gate artifact.
- README contains brief operational guidance, but not the evidence depth required by these checklist items.

## Release assessment

Version 5.0.0 is materially safer as a reference implementation and its local domain tests pass. It should **not be represented as production-complete** until the missing integration, security, resilience, performance, observability, certification, and governance components above are implemented and evidenced.
