# Changelog

## 4.3.0 — 2026-09-23
Closure pass over the v4.2.0 missing-components checklist (MC-001…MC-051).
- Added `service.py` production facade; `errors.py` (23 stable codes, PK_ERROR/1); `validation.py` + 6 JSON Schemas + 13 fixtures.
- Added `config.py`, `controls.py`, `trust.py`, `secret_guard.py`, `store.py`, `telemetry.py`, `precedence.py`, `contract_types.py`.
- `graph.py`: write-ahead commit hook with rollback on persistence failure; O(1) per-tenant node counts; `contains()`; state restore.
- `contract.py` no longer requires `pk_core` (local fallback types); `pk_core>=4.0,<5` declared as optional extra.
- Perf: removed an O(N)-per-request quota scan (≈36× service throughput).
- Tests: 52 production tests (contract, auth, secrets, artifacts, flow control, safety controls, transactions, durability/crash/tamper, lease, disconnected sites, explain, fuzz, concurrency, compatibility, soak) + 16 core tests, all passing normal and -O.
- Docs/governance: owners, 2 ADRs, requirements + traceability, state model, contexts, compatibility, capacity, precedence, security/threat model, failure modes, performance, observability, runbook, support, vulnerability, incident, governance review, waivers, risk register, MASTER.md.
- Tools: run_checks, perf_gate, gen_requirements, build_release (manifest + CycloneDX SBOM + reproducible zip), exit_gate.
- Exit gate: NO_GO pending owner approval of 8 proposed waivers (all automated gates pass).

# Changelog - PLN-01

## 4.2.0 - 2026-09-22

Audit, repair, hardening, and version-bump pass.

### Core correctness and isolation

- Split the standard-library graph/planner into `graph.py`; `pk_core` integration is now lazy so the core can be tested standalone.
- Added strict node/dependency validation, defensive spec copies, JSON-finite validation, and explicit bounded input limits.
- Closed the documented environment-boundary defect: dependencies are now refused across both tenants and environments.
- Added dependency-safe retraction; nodes with dependents are refused unless explicit cascade is requested.
- Idempotent re-declarations no longer increment graph version.

### Concurrency, replay, history, and audit

- Added `expected_version` optimistic concurrency and a thread-serialized mutation critical section.
- Added bounded `request_id` replay refusal.
- Added bounded delta history, graph snapshots, deterministic diffs, and rollback that restores old state as a new version.
- Added a bounded SHA-256 hash-chained in-memory audit trail for accepted, rejected, and no-op mutations.
- Added deterministic plan fingerprints and an explicit rollback target.

### Performance and testing

- Replaced repeated whole-graph history copies with bounded deltas after audit benchmarking exposed pathological scaling.
- Replaced repeated scan-based topological ordering with a deterministic heap-based Kahn traversal, O(V+E log V).
- Added standalone tests for isolation, validation, defensive copying, idempotency, stale writers, threaded atomicity, replay, safe retraction, rollback/diff, resource limits, plan fingerprints, and audit verification.
- Verified the same core suite under normal Python and `python -O`.
- `pk_core` conformance tests remain conditional because `pk_core` is not bundled in the supplied archive.

### Documentation and audit truthfulness

- Removed the false README claim that `MASTER.md` is bundled; its absence is now reported as a residual artifact gap.
- Added `POST_UPDATE_AUDIT.md` and machine-readable `AUDIT_RESULTS.json` enumerating remaining production components.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::IntentGraph.declare: edges to undeclared nodes were accepted and silently treated as satisfied by order() -> KeyError for unknown dependency
- component.py::IntentGraph.declare: self-dependency accepted (only surfaced later as a cycle) -> CycleError at declaration
- component.py::IntentGraph.declare: empty/non-str tenant, environment or name accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
