# Changelog - GAP-01

## 5.0.0 - 2026-09-22

Production-components overhaul driven by the *Professional Missing-Components Checklist v1.0.0* (70 components × 30 checks).

### Added
- Production controller (`controller.py`): signed/validated request pipeline, WAL + checkpoint persistence, idempotent `request_id`s, deny-by-default authorization, rate limiting, drain deadline scheduler with force-kill and reclaim proof, cordon acknowledgement by generation, partition state machine, fail-safe emergency mode, persistent emergency disable, resource-pressure gating, restart reconciliation, watchdog + systemd notify, readiness/liveness/metrics probes, diagnostics explain bundle.
- Durable state store, hash-chained audit log, backup/restore (+ verified scheduled backup), schema migration engine.
- Health signal registry with required/optional signals, per-signal staleness, reporter allow-lists and quorum.
- Runtime adapter protocol with a real POSIX process adapter and a fault-injectable fake.
- Hardware inventory adapter, node identity/boot attestation (software), signed config and release-manifest verification at boot.
- Versioned JSON Schemas for `PK_NODE_LIFECYCLE/1`, `PK_DRAIN/1`, `PK_NODE_HEALTH/1` and the error model; 21 conformance fixtures; 4 recorded protocol sequences.
- Tests: 77 (74 run here; the 3 pk_core conformance tests skip without pk_core) across unit, property (300 seeds), concurrency, fuzz, telemetry contract, real-process integration, release-integrity and SIGKILL chaos. Tooling: stdlib coverage, benchmarks + regression gate, fleet soak, evidence generator, traceability matrix, release manifest + SBOM, exit gate.
- Deployment: hardened systemd unit, sysusers/tmpfiles, example config/signals, Prometheus alert rules, CI workflow.
- Docs: ADRs, normative requirements, STRIDE threat model with test mapping, runbooks, capacity, platform/compat matrix, observability, security/support/EOL policy, dependencies, ownership, named exceptions.

### Fixed (found by the new tests)
- A drain intent could outlive a `draining → cordoned` transition and crash the next tick (found by the property test).
- Draining real processes could block the controller lock for the whole grace period; drain signalling is now non-blocking and the scheduler owns the grace window.

### Compatibility
- `NodeSupervisor` API unchanged. `PK_DRAIN/1` gains additive fields. Persisted state schema 2 (auto-migrates from 1).


## 4.2.0 - 2026-09-22

Audit, repair, hardening, and package-integrity pass.

### Fixed / hardened

- Extracted dependency-free supervisor runtime into `supervisor.py`; package import no longer hard-fails when optional `pk_core` integration is unavailable.
- Rejected future-dated health evidence and monotonic-clock regressions.
- Added initialization validation for state, node identity, workloads, trust classes, health signals, and ticks.
- Rejected duplicate workload identities instead of silently overwriting admission state.
- Made repeated identical drain-deadline breach polling idempotent.
- Added timing context to `PK_DRAIN/1` results.
- Added dependency-free behavioral regression tests.
- Removed the incorrect README claim that `MASTER.md` is included.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`; full production conformance is no longer implied by this standalone archive.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::NodeSupervisor.accepts_placement: documented "only on fresh health evidence" but ignored health -> requires healthy_at(clock), clock = latest observed tick
- component.py::NodeSupervisor.drain: `deadline` accepted but never compared (stubborn workloads always breached) -> breach/escalate only when now > deadline, otherwise report incomplete without escalation
- component.py::NodeSupervisor.drain: re-running a drain on a draining node raised IllegalTransition (draining->draining) -> only transition when not already draining
- component.py::NodeSupervisor.admit: unknown trust class accepted, later crashing drain_order with ValueError from .index(); empty names accepted -> validate at admission
- component.py::NodeSupervisor.report_health: empty signal name accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
