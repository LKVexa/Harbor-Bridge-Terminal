# GAP-03 audit report — v4.2.0

Date: 2026-09-22  
Input version: 4.1.0  
Output version: 4.2.0

## Executive result

The 4.1.0 archive was a small conformance-oriented package with sound basic locality ordering but several production-significant gaps in its runtime semantics. The 4.2.0 pass fixes the defects that can be resolved locally without inventing missing external control-plane systems, then explicitly inventories the remaining production components.

## Defects found and fixed

1. **Physical-capacity overcommit through reservations.** A tenant whose reservation exceeded physical capacity could claim beyond actual free slots because the old logic only protected reservations. **Fix:** every claim now checks total physical free capacity and reservation protection.
2. **Oversubscribed reservation ambiguity.** If total reservations exceeded estate capacity, the first tenants could consume space although the configuration promised mutually impossible floors. **Fix:** the state is detectable (`reservation_deficit`, `oversubscribed`) and claims fail closed with `ReservationOversubscribed`.
3. **Anti-affinity not actually strict.** The old penalty was 100 while a cross-region locality score was 101; an already-used same-site/same-node candidate could still outrank an unused remote site. **Fix:** the spread penalty is greater than the maximum static locality cost, guaranteeing unused site domains rank first when spreading is requested.
4. **Missing fairness verdict in scoring output.** The contract requires the fairness verdict alongside the score, but `rank()` returned node IDs only. **Fix:** added `FairnessVerdict`, `CandidateScore`, `ScoringResult`, and `score_candidates()` while preserving `rank()` for compatibility.
5. **Silent topology re-parenting.** Re-declaring a node silently overwrote its region/site/rack path. **Fix:** conflicting rewrites require explicit `replace=True`; identical declarations remain idempotent.
6. **No point-in-time topology for one score pass.** A mutable topology could change between individual candidate lookups. **Fix:** scoring operates on an immutable snapshot with a generation number.
7. **Weak label canonicalization.** Whitespace-only/ambiguous slash/control-character labels could enter the topology/tenant accounting. **Fix:** canonical validation rejects them.
8. **Duplicate candidates.** Duplicate candidate IDs could be returned more than once and distort downstream placement logic. **Fix:** duplicate candidate lists are rejected.
9. **No release primitive.** Capacity could be claimed but not safely returned. **Fix:** added atomic `release()` with underflow checks.
10. **In-process claim race.** Concurrent claims could read the same free capacity before either update became visible. **Fix:** fair-share verdict/claim/release accounting is serialized with an in-process `RLock`.
11. **Score-to-commit staleness.** A non-mutating fairness verdict could become obsolete before the caller committed the claim. **Fix:** verdicts carry a deterministic state token; `claim(..., expected_state_token=...)` rejects stale local state.
12. **Runtime unnecessarily coupled to gate framework.** Importing the package previously pulled in `pk_core` immediately. **Fix:** stdlib-only runtime logic moved to `scheduler.py`; gate/contract objects are lazy-loaded.
13. **Evidence-path drift.** The gate adapter would have referenced runtime symbols as if they still lived in `component.py`. **Fix:** evidence references now point to `scheduler.py` and the adapter exercises the new strict-spread and fairness-result behavior.
14. **README provenance error.** The archive claimed `MASTER.md` was bundled, but it was absent. **Fix:** the README now records the absence instead of treating it as evidence.

## Verification performed

- Python syntax compilation for all package and test modules: **PASS**.
- `tests/test_scheduler_runtime.py`: **17/17 PASS**.
- Same runtime suite under `python -O`: **17/17 PASS**.
- Non-gating 1,000-candidate local benchmark harness executes successfully; production SLO certification remains outstanding.
- Standalone package import without `pk_core`: **PASS** for runtime API.
- `tests/test_component.py`: **3 tests skipped** in this isolated archive because `pk_core` is not bundled. This is expected and is not counted as production certification.

## Compatibility notes

- Existing construction patterns such as `Topology()`, `topology.place(...)`, `topology.cost(...)`, `FairShare(...)`, `claim(...)`, and `rank(...)` remain available.
- A conflicting `Topology.place()` call that previously overwrote an existing node now raises `TopologyConflict` unless `replace=True` is supplied. This is an intentional hardening change.
- A reservation set with total reserved slots greater than capacity can still be represented for diagnostics, but new claims fail closed until the configuration is corrected.
- `rank(..., spread_from=...)` now treats spreading as a strict site-domain preference rather than a best-effort soft penalty.

## Production readiness boundary

Version 4.2.0 hardens the local runtime but does **not** manufacture absent distributed-system components. In particular, it does not provide durable replicated state, cross-process consensus/fencing, authenticated external APIs, wire schemas, telemetry exporters, a deployment controller, or the adjacent GAP/SCH/PLN services. Those omissions are enumerated in `MISSING_COMPONENTS.md` and should remain visible rather than being marked satisfied by contract prose alone.


## v4.3.0 addendum (2026-09-22)

- Control-plane suite: 244 tests in `tests/cp/` + the 20 v4.2.0 tests; full run 264 tests, 0 failures, 3 skipped (pk_core);
  identical result under `python -O`.
- Checklist execution (`evidence/SUMMARY.json`): 1,380 checks -> 1,100 LOCALLY_VERIFIED, 280 BLOCKED, 0 FAILED,
  0 WEAK_BINDING, 0 UNBOUND; RTM validation: 0 broken references, 0 missing invariant tests, 0 orphan tests.
- A relevance guard (content-word overlap between a check and its bound test) plus a manual semantic review downgraded
  or re-bound every over-claimed binding before this result; 8 defects were found and fixed along the way.
- Exit gate: NO_GO (no sign-offs, blocked P0/P1 checks, missing production evidence classes). This is the honest state.
