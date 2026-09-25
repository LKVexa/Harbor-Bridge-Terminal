# Changelog - INV-35

## 4.3.0 - 2026-09-22

Closure pass executing `inv35_v4.2.0_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST.md` (103 work packages).

### Safety core (`io_model.py`)
- Optional `depth_limit`, `chain_limit`, `byte_limit` on `VirtQueue` (validated; can only tighten the compiled ceilings). All 4.2.0 invariants and tests unchanged.

### New runtime (`runtime/`)
- Separate `ControlPlane` (orchestration) and `Datapath` (bulk) entry points with disjoint capability actions (ADR-0001).
- HMAC-SHA-256 capabilities scoped by tenant/queue/action, TTL, optional single-use nonce replay window, key rotation/retirement, fail-closed key/time outages.
- Stable error registry `INV35-Exxx` with success/degraded/retryable/terminal classes.
- Tenant quotas (share + token bucket), circuit breaker, deadlines, cancellation, idempotency (survives restart), bounded retry with full jitter.
- Lifecycle state machine, degraded modes, live quarantine/freeze/disable, controller epoch fencing.
- Declarative config with secure defaults, four deployment profiles, tighten-only override layers, provenance digests, atomic apply, rollback, secret refusal.
- Metrics (Prometheus text), JSON logs with correlation ids, W3C trace context, decision records, operator explain view, status surface, stall detection.
- Tamper-evident audit chain; journal-based crash recovery into FROZEN.
- Release gate: manifest, CycloneDX SBOM, in-toto/SLSA provenance, Nexus spec manifest, sealed gate results, governance evaluation.

### Measured optimisation
- Verified-capability cache: facade submit+complete p50 ~100 µs → ~42 µs (reference model, CPython 3.11).

### Tests
- 35 → 139 tests: contracts against generated schemas, 19 conformance fixtures, seeded fuzzing (rings, wire, tokens), contention, 28 adversarial cases, sandbox policy, fault injection, partition, adjacent-layer doubles, compatibility matrix, performance gate, release gate.

### Governance / operations
- OWNERS (roles pending), CODEOWNERS, SECURITY.md, approvals register, waivers/tech-debt register, review schedule, license decision (pending), SLOs, rollout/rollback, incident response, patching/EOL, statelessness decision, runbooks, dashboards, alerts, CI workflow, static-analysis and secret-scanning config.

### Status
- `VERIFY=PARTIAL` by design until owner approvals, license, pk_core pin, evidence key and rollout drill exist.

## 4.2.0 - 2026-09-22

Second audit, correctness, hardening, and fail-closed verification pass.

### Datapath correctness and security

- Extracted the security-critical ring model to `io_model.py` so it can be tested without `pk_core`.
- Fixed queue-capacity accounting: `QUEUE_DEPTH` now bounds descriptor entries rather than only submitted chains, preventing several maximum-length chains from exceeding the intended descriptor limit.
- Added exact descriptor reservation/release accounting with `in_flight_descriptors` and FIFO completion reservation tracking.
- Added validation for head and next indices, including negative, boolean, string, and floating-point values.
- Added fail-closed validation for non-`Descriptor` ring entries, slot/index mismatches, negative addresses, negative lengths, and non-integer address/length fields.
- Snapshot the caller-provided descriptor mapping before walking it; frozen descriptors prevent post-snapshot field mutation.
- Guest-memory validation now accepts fully covered adjacent/overlapping registered regions while rejecting any gap.
- Added queue locking so concurrent submissions cannot overcommit the descriptor bound.
- Completion notification input is type-checked and failed completion calls do not mutate state.
- Completion history remains bounded at `QUEUE_DEPTH`.

### Test/gate hardening

- Added standalone unit tests for hostile descriptor shapes, memory coverage, descriptor-depth accounting, failed-mutation invariants, notification liveness, bounded history, and concurrent submissions.
- Added repository-integrity tests for version consistency, checklist cardinality/IDs, audit artifacts, and documentation/file consistency.
- Changed the `pk_core` conformance test so it verifies 100 finding records without treating a blanket passing status as proof of production readiness.
- Added `verify.py` and Windows `VERIFY.cmd`. Verification now exits with code `2` when local checks pass but `pk_core` is unavailable, eliminating the prior false-green condition where all conformance tests were skipped yet unittest reported `OK`.
- Package import no longer requires `pk_core`; only `COMPONENT`, contract metadata, and certification bindings are lazy-loaded.

### Audit/reporting

- Removed the stale README claim that `MASTER.md` was included; that file is absent from the supplied repository.
- Added `AUDIT_MATRIX.json`, `AUDIT_REPORT.md`, and `MISSING_COMPONENTS.md`.
- Post-update checklist audit: 8 present, 23 partial, 69 missing. The repository therefore remains a hardened reference component, not a production-certified implementation.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and assess bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: refusal-backed findings gained explicit failure branches.
- `tests/test_component.py`: stdlib conformance test added.
- `VERSION` and `__version__` added.

### Defects fixed

- Descriptor slot/index mismatch refused.
- Non-integer address/length rejected rather than surfacing an incidental `TypeError`.
- Completion history bounded.

### Historical gate note

The 4.1.0 changelog stated that all 100 requirements were satisfied. The 4.2.0 audit corrects that interpretation: the supplied archive lacks `pk_core` and most production evidence/artifacts, so that statement cannot be substantiated from this repository alone.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
