# Changelog - PLN-05

## 4.2.0 - 2026-09-23

Missing-component remediation pass driven by `source/PLN05_v4.1.1_Missing_Component_Remediation_Checklists.md` (MC-01..MC-34, 1 468 boxes). Item-level results: `evidence/4.2.0/MC_STATUS.json` and the annotated copy `evidence/4.2.0/CHECKLIST_EXECUTED.md`.

### Added
- Service boundary `plane.py` around the unchanged controller: boundary codec, authentication/authorization, emergency controls (freeze/quarantine/disable/drain, two-person resume), freshness and stale/degraded modes, idempotency and ordering, lease/epoch leadership, persist-before-publish, fenced publication, explain, metrics/logs/traces.
- `wire.py` + `schemas/` (PK_DEMAND/1, PK_CAPACITY_LIMITS/1, PK_CAPACITY_TARGET/1, PK_ERROR/1); fixture corpus (14 valid, 64 invalid, 8 sequences) with a pinned manifest.
- `iam.py`, `keys.py`, `security/` (capabilities policy, threat model T01–T20, isolation, crypto, security-dependency failure policy, approved versions).
- `configuration.py` + `config/` (layered overlays, validation, atomic journalled activation, rollback, secret-reference rule).
- `state.py` (HMAC-sealed crash-consistent state with migration, lease service, fenced reference consumer), `audit.py`, `reliability.py`, `health.py`, `telemetry.py`, `supplychain.py`, `cli.py`.
- Tests: units, plane integration, contract fixtures, adversarial security (one per threat), fault harness (FS01–FS19), fuzz/property, concurrency, compatibility, soak/burst/fleet, alert scenarios, repository checks.
- Benchmarks + performance gate, efficiency analysis, spec/NFR/state machine, ADR-0001 (PROPOSED), runbooks, release policy, ownership/escalation record (roles UNASSIGNED), waivers/reviews/approvals registers, traceability matrix, `MASTER.md`, CI workflows, local CI, release builder, exit gate.

### Changed
- `__init__.py` no longer imports `pk_core` eagerly: the runtime works without the framework; `COMPONENT`/`build_contract` load lazily.
- `contract.py` renders `spec.py` (single source for scope and contract data).
- `controller.py`: added `REASONS` (stable outcome/reason codes) and `snapshot()`/`restore()`; decision behaviour unchanged.

### Defects found by this pass's own checks and fixed before release
- Concurrency test: releasing the lock between queue take and decide let a later sample overtake an earlier one (`E_OUT_OF_ORDER` under load); take+decide now share one lock hold.
- Concurrency test: `submit_demand` implemented as enqueue + process(1) could return another caller's decision; now decides its own sample synchronously.
- Fault FS06 design: a state-write failure (disk full) escaped as a raw `OSError` after the controller had already advanced; now `E_STATE_UNAVAILABLE`, nothing published, memory rolled back to match disk.
- Soak leak detector: the in-memory audit list and the reference consumer history grew without bound (~0.8 KiB/decision); both are now bounded windows (audit verification takes the window start).
- Unit test: state scope pattern accepted `../..` segments (file names were hashed, so no traversal, but the scope was invalid); segments must now start alphanumeric.
- Fault FS05/FS15 first versions were confounded by the test key ring's validity window; the helpers now back-date keys, and the health probe itself runs the clock-discontinuity detector.

### Defects found by the independent adversarial review (a separate agent attacking the build) and fixed
- **Stale leader on shared state (critical):** a controller whose lease had lapsed re-acquired it and decided from cached memory, publishing a target above the newer envelope another instance had set and overwriting that envelope on disk. New lease terms now reload the scope from shared state; limits, ceiling lowering, controls and resume require the lease.
- A persistence failure in `submit_limits`, `lower_ceiling`, `control`, `resume` or tick holds escaped as a raw `OSError` and left memory ahead of disk; all authority changes are now transactional (`E_STATE_UNAVAILABLE`, memory rolled back), and audit capacity is checked before a change is applied.
- Site scope was not enforced for explain/status reads or for tenant-wide controls/resume; tenant-wide actions now require `site="*"` and a credential valid for every site.
- A resume proposal never expired and was not bound to the controls it would release; proposals now expire after 15 min and bind to a digest of the control state.
- Authority-expanding actions (limits, resume, config) were accepted during a trusted-time fault; now refused. Quarantine lists are de-duplicated and bounded; pending resumes bounded; nonce purge is O(1) until the cache is full.
- A lowered ceiling or raised floor published nothing until the next demand sample; envelope changes that move the target now publish a `constrained-hold`.
- Found while porting the reviewer's fuzzer into `tests/fuzz/test_multi_instance.py`: two holds at the same instant produced the same `decision_id` and the consumer silently dropped the second (fixed with a persisted per-scope decision sequence); and a lease that had lapsed looked valid again after a wall-clock step backwards (local lease view is now distrusted during a time fault, and an explicit refusal from the coordination service always ends the lease).

### Not done (see AUDIT_REPORT_4.2.0.md)
- Owner decisions: ADR approval, role assignments, license, baseline approval, waiver approval, release sign-off.
- External: `pk_core` and sibling packages, KMS/volume encryption, transport adapters, forge CI execution, multi-platform runs, fleet reference infrastructure, power/thermal measurement.

## 4.1.1 - 2026-09-22

Repository audit, correctness fix, and defensive-hardening patch.

### Correctness and safety

- Extracted the elasticity algorithm into dependency-free `controller.py` so safety-critical behavior can be tested without `pk_core`.
- Validated floor, ceiling, grace count, thresholds, current target, and demand samples with explicit bool/type/finite/range checks.
- Hardened `lower_ceiling()` so it cannot raise the ceiling or silently reduce the declared floor when an external cap is invalid.
- Reset pending scale-down evidence when the active capacity envelope changes.
- Added explicit `hold: at floor` and `hold: at ceiling` reasons instead of reporting a scale action when no target change occurred.
- Re-aligned custom checklist evidence to requirements it actually exercises instead of unrelated checklist positions.

### Verification and documentation

- Added standalone controller unit tests, including optimized-mode parity, independent of the external conformance framework.
- Kept the framework conformance suite, but documented that it requires `pk_core`.
- Removed the stale README claim that a `MASTER.md` file is present when it is not.
- Added a post-hardening audit report identifying remaining production-readiness components not contained in this repository.
- The 4.1.0 “all 100 requirements satisfied” statement is retained as history but superseded by the 4.1.1 evidence audit (13 present / 25 partial / 62 missing).

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::ElasticityController.__init__: initial `current` outside [floor, ceiling] was kept, contradicting "target is always clamped" -> clamp at construction (and require int)
- component.py::ElasticityController.observe: NaN/non-numeric utilisation silently held (NaN) or crashed with TypeError -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
