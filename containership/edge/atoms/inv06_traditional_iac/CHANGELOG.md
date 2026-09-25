# Changelog - INV-06

## 4.3.0 — 2026-09-22 — Missing-component checklist execution

Executed the v4.2.0 Professional-Grade Missing-Component Checklists (72 components, 4,830 controls) against this package.

### Added (package-local, stdlib-only, tested)
- `durable.py` — digest-sealed revision store, CAS-on-serial commits, WAL intent/commit journal with crash recovery, rollback-as-new-serial, verified backup/restore, state-format migration (MC-010, 012, 013, 014, 007).
- `locking.py` — cross-process lease lock with monotonic fencing tokens and a fenced backend (MC-011).
- `graph.py` — dependency graph, cycle/dangling refusal, apply/destroy ordering, replacement fan-out (MC-017).
- `config.py` — pinned `inv06-hcl-subset/1` parser, overlay compiler (global < environment < site), hash-chained provenance ledger (MC-016, 024, 025).
- `policy.py` — fail-closed GAP-13 policy gate, constraint precedence, INV-01/07/08 handoff contracts (MC-009, 022, 023).
- `security.py` — token authentication, default-deny tenant-scoped authorization with separation of duties, purpose-bound HMAC signing with key rotation/revocation, artefact digest verification, redaction, tenant isolation, security-outage policy, signed fsync'd audit log (MC-033–037, 039–041).
- `resilience.py` — deadlines, cancellation, jittered bounded retry, idempotency, admission/load shedding, circuit breaker, degraded mode, freeze with two-person unfreeze, watchdog, offline queue, residency-aware failover (MC-021, 026–031).
- `observability.py` — health/readiness, Prometheus exposition with label guards, JSON logs, W3C trace context, plan explanations, release lineage (MC-043–048).
- `execution.py` — digest-pinned Terraform/OpenTofu runner with sandboxed env and JSON plan parsing, provider allowlist, provider protocol + conformance provider, platform support check (MC-015, 018, 019 contract, 035, 064).
- `release.py` — benchmarks, SLO thresholds, capacity model, copy audit, signed acceptance evidence, canary rollout, production exit gate (MC-051–054, 062, 063, 069).
- `service.py` — `ControlPlane`, the single wired path (authn → authz → freeze/degraded → admission → policy → signed approval → lease → provider → CAS commit → audit/metrics).
- `governance/`, `ops/`, `pyproject.toml`, `LICENSE` (placeholder), `THIRD-PARTY-NOTICES.md`, `tools/build_status.py`, `evidence/`.
- `tests/test_production.py` — 61 tests (contract, adversarial, property/fuzz, fault-injection, cross-process, soak/burst, end-to-end).

### Changed
- `IacState.precheck()` added and `apply()` refactored to share `_check_applicable()`. **Defect found during this pass:** without a pre-provider check, replaying an already-applied plan under a new idempotency key would drive the provider before the stale-serial refusal. `ControlPlane.apply` now prechecks before any provider call.

### Result
Production gate: **NO_GO** (see `evidence/PRODUCTION_GATE.json`): 1 blocked item (MC-001 source not supplied), 6 external items, unsigned evidence (no key supplied), owner sign-offs outstanding. 997 of 4,830 controls evidenced package-locally.

## 4.2.0 - 2026-09-22

Audit, parse, fix, harden, and version-bump pass.

### State-integrity fixes

- Moved plan/apply logic into `state.py` so the safety-critical engine is separable from the `pk_core` adapter.
- Replaced publicly mutable authoritative `resources`/`protected` state with detached/read-only views and controlled mutation methods; callers can no longer bypass serial invalidation by mutating returned containers.
- Added an in-process `threading.RLock` around state transitions. Two plans created against the same serial can race, but only one can commit; the second observes the advanced serial and is refused.
- Protection changes now advance the state serial, invalidating plans computed under the previous protection policy.
- Plan inputs and state values are normalized to detached JSON-compatible data, removing mutable-object aliasing/TOCTOU behavior and rejecting non-finite or unsupported values.
- Apply now constructs the complete next state before replacing the authoritative state reference.

### Plan/interface hardening

- Added strict `PK_IAC_PLAN/1` validation: required/unknown fields, serial type/range, resource identifiers, duplicate deletes, operation overlap, schema version, JSON-compatible values, and integrity metadata are all checked fail-closed.
- Plans now include a deterministic SHA-256 digest over canonical plan contents; accidental or unsanctioned mutation without resealing is detected before state mutation.
- Added machine-readable `IacError` subclasses with stable codes and structured details.
- Added JSON Schema 2020-12 artifacts for plan, state-snapshot, and drift payloads plus a reference plan fixture.

### Drift, audit, and observability fixes

- Drift now distinguishes “resource absent” from “resource present with JSON null” using explicit presence flags.
- Added package-local counters for plans, applies, stale/protected/invalid refusals, drift scans, and current drift count.
- Added a SHA-256 chained in-memory audit ledger and verifier. The ledger records operation metadata, not resource values.

### Test and packaging hardening

- Standalone state-engine tests now run even when `pk_core` is absent; previously the class-level skip meant all meaningful tests could be skipped in an isolated archive.
- Added deterministic optimized-mode coverage and a two-thread same-serial race test.
- Package import no longer fails solely because `pk_core` is absent; the state engine remains usable while the parent-framework adapter is marked unavailable.
- Corrected README claims about the absent `MASTER.md` source artifact and documented the `pk_core` certification limitation.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.

### Validation

- Python syntax compilation: PASS.
- Standalone/unit suite: 12 PASS.
- Parent `pk_core` conformance suite: 2 SKIPPED in the isolated archive because `pk_core` is not bundled.
- ZIP integrity: revalidated after packaging.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `tests/test_component.py`: stdlib conformance test added (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- `VERSION` file and `__version__` added.

### Defects fixed

- `IacState.apply`: protection was re-checked at apply time before mutation.
- `IacState.apply`: delete/update/create state mismatches were validated before mutation and reported as stale plans.

### Gate

The prior release recorded all 100 requirements satisfied under the parent workspace. That result requires the external `pk_core` framework/evidence context and is not independently reproducible from this isolated archive.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
