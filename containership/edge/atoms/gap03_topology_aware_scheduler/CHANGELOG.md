# Changelog - GAP-03

## 4.3.0 - 2026-09-22

Missing-components pass: executes `GAP03_v4.2.0_Missing_Components_Professional_Checklist.md` (46 components x 30
checks + 10 program gates) against a new stdlib-only `controlplane/` package. The v4.2.0 runtime API is unchanged.

- Added `controlplane/` (MC-001..MC-046), `certification/` (checklist runner, blockers, RTM), `governance/`, `policy/`,
  `runbooks/`, `docs/adr`, `docs/components` (generated), `ci/matrix.yml`, `benchmarks/harness.py` + PROPOSED thresholds,
  `tests/cp/` (244 control-plane tests) and `tests/fuzz_corpus/`.
- Checklist result: 1,100 checks locally verified, 280 blocked with named reasons, 0 failed/weak/unbound;
  PG-005 (production consensus) and PG-009 (exercised recovery) blocked; exit gate NO_GO; 0 completion claims.
- Defects found by this pass's own tests/fuzzer/validators and fixed: DEF-01..DEF-08 (see `evidence/DEFECTS.json`).
- Compatibility: `import gap03_topology_aware_scheduler` still needs no `pk_core`; `controlplane` is opt-in.

## 4.2.0 - 2026-09-22

Correctness, concurrency, API-evidence, and packaging hardening pass.

### Runtime separation and compatibility

- Added `scheduler.py` as a stdlib-only runtime module; the `pk_core` dependency is now isolated to the conformance adapter.
- Package-level gate objects are lazily loaded, so core topology/fair-share scoring can be imported without `pk_core`.
- Preserved the existing `Topology`, `FairShare`, `rank`, `COMPONENT`, and contract entry points.

### Correctness fixes

- Fair-share claims now enforce physical free capacity even when a request is still within the tenant's nominal reservation.
- Oversubscribed reservation sets fail closed for new claims and expose a reservation deficit.
- Added atomic `release()` with underflow protection.
- Added deterministic fair-share state tokens and optional stale-score rejection on `claim()`.
- Added explicit, non-mutating `FairnessVerdict` and `score_candidates()` so the required fairness verdict is returned alongside candidate scores.
- Anti-affinity changed from a soft penalty that could still select an already-used site to a strict site-spread ordering when spreading is requested.
- Duplicate candidate identifiers now fail validation.

### Topology hardening

- Added canonical label validation, including rejection of whitespace-surrounded labels, slash-delimited ambiguity, and control characters.
- Conflicting topology re-parenting now requires explicit `replace=True`; idempotent redeclaration remains allowed.
- Added topology generation tracking and immutable point-in-time snapshots so one scoring pass observes one topology version.

### Concurrency and evidence

- Fair-share claim/release operations are protected by an in-process re-entrant lock.
- Added 17 stdlib runtime tests covering monotonic locality, unknown-node refusal, rewrite conflict handling, strict spreading, duplicate candidates, corruption refusal, capacity enforcement, oversubscription, release underflow, invalid ledgers, stale score tokens, an exhaustive small-state reservation invariant, concurrent claims, and score/fairness output.
- Runtime tests pass in normal and `python -O` modes.
- Added a non-gating 1,000-candidate local benchmark harness for diagnostic SLO measurements.
- Updated gate evidence paths from historical `component.py` runtime locations to `scheduler.py`, and the adapter now exercises strict spreading and score-with-fairness behavior.

### Audit corrections

- README no longer claims the absent `MASTER.md` is bundled.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.
- Clarified that local conformance output is not equivalent to production implementation/certification of every checklist control; the historical 4.1.0 "all 100 requirements satisfied" statement is therefore treated as local gate status, not full production evidence.
- Added `MANIFEST.sha256` for deterministic package-integrity checking (unsigned; not a substitute for release signing/SBOM provenance).

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Topology.cost: two distinct nodes in the same rack cost the same as nodes in different racks (both 1), so locality was not monotone -> each level adds 1 on top of LEVEL_COST, giving node < rack < site < region
- component.py::Topology.cost: cost(x, x) returned 0 for a node outside the topology, bypassing the "refuse to score outside topology" rule -> resolve path first
- component.py::FairShare.claim: zero/negative/non-int slots accepted (a negative claim silently released capacity) -> ValueError
- component.py::Topology.place: empty/non-string labels accepted -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
