# Changelog

## 4.3.0 - 2026-09-22

Overhaul against the *GAP-14 v4.2.0 Missing Components Engineering Checklist* (40 components, 1,831 items). Status per item: `CERTIFICATION_MANIFEST.json`.

### Added
- `service.py` DecisionService: authenticated, admitted, deadline-bound decision path over signed estate inputs; signed provenance envelope; audit-before-return; explain; PLN-06 handoff; what-if simulation; advisory DAG planning; outcome recording for calibration; readiness/drain.
- `adapters.py` GAP-13 / GAP-03 / GAP-05 / SCH-01 readers and PLN-06 idempotent handoff (signature, issuer, freshness, skew, binding, version-watermark checks).
- `identity.py` capability tokens and `WorkloadIdentity`; `trust.py` canonical JSON, HMAC key ring with issuer/validity/revocation, strict validators, replay guard; `errors.py` reason-code registry (category + disposition + operator action).
- `audit.py` hash-chained MAC'd audit (memory + fsync'd file sink, chain verification); `config.py` signed transactional configuration with rollback, knob table and production dev-flag refusal; `compat.py` pk_core handshake and gate-integrity evaluator.
- `resilience.py` deadlines, cancellation, bounded jittered retry (idempotent only), circuit breaker, admission control (global + per-tenant), freshness and stale-data policies.
- `observability.py` bounded-cardinality metrics with Prometheus exposition, redacting size-bounded JSON logger, W3C trace context.
- `planner.py` multi-dimensional planner (partial, amortised, replicate, carbon/thermal, transfer time, storage/IOPS, compatibility, quota) and DAG optimiser; `modeling.py` Page-Hinkley drift detection and canary router.
- 17 new JSON Schemas (`tools/gen_schemas.py`), stdlib schema validator (`schema_check.py`), CLI (`__main__.py`), `pyproject.toml`, `tools/bench.py`, `tools/release_evidence.py`, `tools/build_manifest.py`.
- Tests: security/adapters, evidence/config/gate, operability, property/fuzz, fault-injection matrix (single + pairwise), P2 capabilities, packaging.
- Docs: `docs/DESIGN.md`, `docs/OPERATIONS.md`, `docs/RUNBOOKS.md`, `docs/COMPATIBILITY.md`, `docs/SUPPLY_CHAIN.md`, `OWNERS.md`.

### Changed
- `contract.py` lists the new interfaces and signals. `GravityManager` / `PK_GRAVITY_RECOMMENDATION/1` unchanged.
- `canonical_json` uses the native encoder with `allow_nan=False` (5x faster signing path).
- Default `max_concurrent` is 4 per process (CPU-bound; see bench evidence).

### Security
- Revoked or unknown signing keys cannot sign; audit signing failure withholds the decision.
- Requests are authenticated before the body is parsed.

# Changelog - GAP-14

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening and release-evidence pass.

### Runtime and correctness

- Extracted the production decision logic into dependency-free `engine.py`; `pk_core` is now needed only for the conformance component.
- Cross-site locality multipliers must be explicit; missing cost data raises machine-readable `CostModelError` instead of silently assuming `1.0`.
- Hardened dataset/configuration validation against empty identifiers, bool-as-number inputs, negative values, NaN, infinity, malformed route keys, and invalid convergence flags.
- Snapshot/freeze manager configuration to prevent caller mutation from changing live decision semantics.
- Added asymmetric per-route egress pricing and explicit exact-cost tie policy (prefer move-compute).
- Added structured cost breakdowns, reason codes, elimination details, and coded exceptions while retaining legacy result fields.
- Co-located data at a residency-illegal site now fails closed rather than returning a healthy no-op.

### Verification and release artifacts

- Added 11 standalone engine unit tests that execute without `pk_core`.
- Added always-on package/checklist integrity tests; tightened conformance partial handling.
- Added JSON Schemas for PK_DATASET/1, PK_MOVE_COST/1 and PK_GRAVITY_RECOMMENDATION/1.
- Restored the missing `MASTER.md` as a checklist-derived v4.2.0 master prompt/workflow artifact with explicit provenance.
- Added `AUDIT_REPORT_v4.2.0.md`, `MISSING_COMPONENTS.md`, example usage, and release manifest generation.

### Gate status

- Standalone engine verification: PASS.
- Full `pk_core` 100-check gate: not executable from this isolated archive because `pk_core` is external; recorded as a P0 residual dependency rather than silently skipped as production evidence.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Dataset: negative/NaN/non-numeric size_gb and empty names accepted, so a negative size made move-data "cheapest" and bypassed the cost model -> validate in __post_init__ with ValueError
- component.py::GravityManager.move_data_cost/move_compute_cost: negative or NaN distance multipliers produced negative costs that won every comparison -> shared _multiplier helper rejects them with ValueError
- component.py::GravityManager.recommend: co-located response omitted the "to" and "eliminated" keys every other recommendation carries (KeyError for consumers) -> include them

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
