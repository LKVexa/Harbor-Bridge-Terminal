# Changelog - INV-72

## 4.3.0 - 2026-09-23

Applied `INV72_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (91 targets: 65 missing, 24 partial,
2 externally unverified) through the junkyard chop shop.

### Added
- Governed service (`service.py`) composing authentication, authorization, admission, deadlines,
  cancellation, config limits, precedence, verified inventory, atomic fenced reservation, audit,
  metrics/logs/traces and a retained decision ring for `explain()`.
- `state.py` reservation store: atomic reserve, idempotency keys, fencing, write-ahead hash-chained
  journal with crash recovery, snapshot/restore, quarantine/drain/revoke.
- `discovery.py` authenticated inventory intake (digest + HMAC, monotonic generation), freshness and
  offline grace per tier, verified-only failover.
- `trust.py` HMAC caller tokens with replay cache and capability/tenant authorization.
- `config.py` + `config/profiles` (cloud, datacenter, near_edge, far_edge), overlays, validation,
  secret refusal, provenance, atomic generations, operator and automatic rollback.
- `errors.py` stable reason/error codes with outcome classes; `lifecycle.py`; `compat.py`;
  `precedence.py`; `capacity.py`; `adapters.py` (GAP-02/GAP-11/INV-68/INV-69 seams).
- Seven versioned JSON Schemas and a strict stdlib validator; 15 golden conformance fixtures.
- `audit.py` tamper-evident audit chain; `telemetry.py` bounded metrics, structured logs, W3C trace
  context; `redaction.py`; `explain.py`.
- Documented bounds (`MAX_INVENTORY`, `MAX_COUNT`, `MAX_ID_LEN`, …) and `LimitExceededError`
  (a `ValueError` subclass, so v4.2.0 callers still catch it).
- ops/ (SPEC, threat model, boundaries, runbook, incident, owners, escalation, waivers, reviews, EOL,
  compatibility policy/matrix, telemetry policy, alerts, dashboards, perf thresholds, RTM), ADR-0001.
- tools/ (rtm, governance_check, deps_check + SBOM, manifest, perf_gate, pk_gate, release_gate,
  bootstrap); bench/perf_suite.py; declared CI; vendored pk_core.
- Tests: v43 control suites, property fuzzing, concurrency, fault injection, adversarial, gate
  falsifier.

### Fixed (defects in the v4.2.0 candidate)
- A whole device could be handed to two jobs of the same tenant: ownership was tracked per tenant,
  not per reservation. The reservation store now occupies a reserved whole device for every later
  request (`StateStoreTest.test_same_tenant_cannot_get_one_whole_device_twice`). `match()` keeps the
  legacy behaviour for compatibility and is deprecated as an ownership record (D-001).
- `component.py` bound its two exercised checks to the wrong checklist items: the matching check to
  C031 (pin approved technology) and the isolation check to C041 (threat model). Rebound to C081 and
  C046.
- No input bounds: an unbounded generator as inventory was materialised in full; now refused at
  `MAX_INVENTORY + 1` without further reading.

### Changed
- Package version 4.3.0; `pk_core` conformance tests now run (no skips).

### Deprecated
- D-001: using `match(reserve=True)` mutation of `Device.tenants` as the ownership record
  (removal 5.0.0).

## 4.2.0 - 2026-09-22

Repository audit, correctness hardening, and testability pass.

### Correctness and security

- Moved security-critical device matching into dependency-free `matcher.py`.
- Changed missing isolation to the fail-closed `dedicated` default and reject unknown isolation values.
- Reject boolean numeric values, NaN/infinite memory, malformed strings, non-boolean interconnect flags, duplicate device IDs, and invalid/mutated inventory.
- Made selection deterministic across caller inventory ordering.
- Added `reserve=False` for side-effect-free eligibility checks and preserved atomic reservation only after a complete selection succeeds.
- Added explicit `RequirementValidationError` and `InventoryValidationError` exception types.

### Packaging and integration hardening

- Added dependency-free metadata and lazy loading so the pure matcher/package version can be imported without `pk_core`.
- Corrected the contract interface description to match the implemented request, inventory, and match surfaces.
- Corrected behavioural evidence references from `component.py::match` to `matcher.py::match`.
- Removed the README claim that a missing `MASTER.md` artifact was included.
- Rewrote runtime instructions to distinguish local verification from the external `pk_core` gate.

### Verification

- Added standalone matcher tests covering validation, isolation, deterministic selection, interconnect selection, cross-tenant refusal, reservation atomicity, and malformed inventory.
- Changed the package/version test so it runs even without `pk_core`; only the external integration tests are skipped when the dependency is absent.
- Added repository-integrity tests for checklist sequencing, version synchronization, missing README references, and optimizer-sensitive bare asserts.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md` so unimplemented production controls are explicit rather than silently inherited from framework defaults.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::match: whole (non-partition) devices already assigned to one tenant were handed to another tenant -> refuse with reason
- component.py::match: missing req keys raised KeyError; count<=0/non-int or negative mem_gb accepted (count=0 "matched" nothing) -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
