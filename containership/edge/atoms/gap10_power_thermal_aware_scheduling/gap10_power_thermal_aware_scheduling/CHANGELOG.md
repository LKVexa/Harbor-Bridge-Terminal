# Changelog - GAP-10

## 4.3.0 - 2026-09-22

Missing-components pass: the 40 capabilities listed in `MISSING_COMPONENTS.md` (v4.2.0 audit) built as a stdlib-only `production/` layer on top of the unchanged v4.2.0 kernel, executed against `GAP10_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (2,020 items).

### Added
- `production/` package: authenticated GAP-09 telemetry adapter, multi-sensor aggregation, calibration inventory, rate-of-rise predictor, battery runtime estimator, cooling-domain correlation, GAP-11 accelerator integration, workload-class shedding, constraint precedence, fenced durable state store, signed policy service (content-addressed revisions, CAS activation, canary staging, rollback, two-person relaxation, shadow evaluation), leader leases with fencing tokens, restrict-only operator controls, retry/backoff/circuit breaker, partition semantics, trusted clock, scoped key ring, error taxonomy, hash-chained audit sink, Prometheus exporter, structured logging with trace context, health/readiness and explain APIs, scheduler and elasticity enforcement adapters, consumer-side fail-closed view, canary rollout controller, schema validator.
- Schemas `PK_TELEMETRY_ENVELOPE/1`, `PK_GAP10_HEALTH/1`; `PK_POWER_CEILING/1` gains optional provenance fields (required set unchanged).
- Tests: `test_prod_p0..p3`, `test_prod_docs`, golden vectors, telemetry and policy fuzzing, concurrency, fault injection; `tools/run_all_tests.py` machine-readable report failing on unwaived skips.
- Tools: `bench.py` (fleet/soak), `build_release.py` (reproducible ZIP + signed provenance), `build_evidence.py` (checklist traceability matrix).
- Ops/governance: alerts, dashboard, compatibility matrix, SBOM, dependency policy, runbook with RTO/RPO and backup/restore, incident severity, ADRs, exception register, ownership slots.

### Fixed during the pass (found by the new tests)
- Partition autonomy window never expired when the partition began at t=0 (`partitioned_at or now` falsy bug).
- A list-typed `attestation` field crashed ingestion with `TypeError` (found by fuzzing); now rejected as unauthenticated.
- Concurrent policy activations with the same parent all succeeded (last writer wins); activation is now compare-and-swap.
- Audit sink retained every entry in memory (unbounded growth in the 200-node soak); now bounded when file-backed.
- Per-identity rate limiting starved a single GAP-09 aggregator serving many nodes; limit is now per (identity, node).

### Behavioural notes
- Package `__init__` no longer requires `pk_core`; the estate component is exported only when `pk_core` is importable.
- Uncalibrated hardware now uses a conservative profile (emergency 65 C) instead of generic defaults.

## 4.2.0 - 2026-09-22

Audit, contract-alignment, and hardening pass.

### Correctness fixes

- Implemented actual power-budget-aware scheduling; v4.1.0 claimed power-state ownership but only temperature and battery affected the ceiling.
- Non-finite temperatures (`NaN`, `+/-inf`) now fail closed as unusable evidence instead of allowing `-inf` to appear nominal.
- Added explicit stale, excessive-future, and out-of-order/replayed telemetry handling with bounded clock skew.
- Added policy validation so malformed threshold ordering, hysteresis margins, ceiling fractions, battery reserves, and freshness windows fail before activation.
- Added validation for node identifiers, initial bands, power budgets, physically plausible temperature bounds, and freshness argument pairs.
- Fixed the README reference to a nonexistent `MASTER.md` file.

### Hardening

- Extracted the deterministic stdlib-only kernel to `model.py`, removing `pk_core` as a prerequisite for unit-testing the safety logic.
- Added thermal, battery, and power constraints with a most-restrictive-wins decision rule.
- Added hysteretic recovery for both thermal and power pressure plus a battery recovery margin.
- Added structured decision reasons, telemetry status, and ceiling fraction to `PK_POWER_CEILING/1` output.
- Added versioned JSON Schemas and conformance fixtures for all three documented GAP-10 interfaces.
- Added standalone unit coverage for boundary conditions, invalid inputs, stale/future telemetry, power overload, battery recovery, and schema/fixture parsing.
- Preserved `_verify()` checks so estate conformance behavior is unchanged under `python -O`.

### Audit transparency

- Corrected conformance evidence mappings so behavioral proof is attached to the checklist requirement it actually demonstrates.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.
- Clarified that answering the 100-item checklist is not equivalent to proving every production subsystem has been implemented.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and `assess_*` bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `tests/test_component.py`: stdlib conformance test for 100 findings, no unexpected partial/blocked findings, optimized-mode parity, and version pin.
- `VERSION` file and `__version__` added.

### Defects fixed

- NaN/non-numeric temperature treated as missing evidence rather than nominal.
- Battery below reserve sheds nominal and elevated states to critical.
- Invalid battery fractions rejected.
- Negative/non-integer full capacity rejected.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
