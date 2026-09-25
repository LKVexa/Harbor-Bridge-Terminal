# GAP-14 Data-gravity manager — Audit / Overhaul Report v4.3.0

**Input:** v4.2.0 (`gap14_data_gravity_manager_v4.2.0_Audited_Hardened.zip`)  
**Work contract:** *GAP-14 v4.2.0 Missing Components — Professional Engineering Checklist* (40 components, 1,800 component items + 31 program items = 1,831)  
**Output:** v4.3.0 · **Date:** 2026-09-22

## Verdict

**Production certification: NO-GO** (unchanged, and now for narrower, explicit reasons). v4.3.0 implements GAP-14's side of every P0 contract and most P1/P2 capabilities, proven against signed fixtures; the remaining P0 gates require things that cannot exist inside this archive: a certified `pk_core`, live GAP-13/GAP-03/GAP-05/SCH-01/PLN-06 runs, signed release artifacts, named owners and a security review.

## Item status (all 1,831 — `CERTIFICATION_MANIFEST.json`)

| Status | Items | Meaning |
|---|---:|---|
| implemented | 763 | code in this package, verified by a test (dedicated, or indirect/by construction — see sampling below) |
| implemented-fixture | 43 | GAP-14 side done, verified against signed fixtures; live counterpart pending |
| documented | 383 | normative docs satisfy the item (design, operations, runbooks, compatibility) |
| partial | 346 | note states exactly what is missing |
| open | 102 | not implemented in v4.3.0 (listed below) |
| external | 161 | needs people, live estate, other OS/runtimes, signing, or human exercises |
| not-applicable | 33 | with justification |

## What changed (summary — full list in CHANGELOG.md)

13 new modules (service, adapters, identity, trust, errors, audit, config, compat, resilience, observability, planner, modeling, schema_check) + CLI; 17 new wire schemas; 8 new test modules; design, operations, runbook, compatibility and supply-chain documents; benchmark and release-evidence tooling.

## Verification performed

* Test suite: see `evidence/test_report.json` (stdlib `unittest`; the only skips are the two `pk_core`-dependent conformance tests).
* Property tests: engine legality/minimality/tie-break invariants; planner ≡ v4.2.0 engine without a profile (400 cases per run, 3,000 checked during the overhaul).
* Fuzz: malformed requests always refused with a registered, non-internal code; config fuzz never activates an invalid revision.
* Fault injection: 4 dependencies × 7 faults single matrix and all cross-dependency pairs; invariant "correct audited decision or registered refusal with no decision record" held in every case.
* Benchmark (`evidence/bench_v4.3.0*.json`, in-process with signed fixtures, CPython 3.11, x86_64): single worker p50 ≈ 0.6 ms, p99 ≈ 1.2 ms, ~1.5 k decisions/s; engine-only p99 in the microseconds. **Finding:** 8 threads in one process push p99 above 50 ms (GIL contention) → default `max_concurrent` lowered to 4 and deployment guidance set to one worker per core.

## Independent verification of the manifest

An independent reviewer agent sampled 30 `implemented`/`implemented-fixture` items twice (seeds 7 and 2026, ≥ 25 per sample from the component-specific sections) under a strict rule: *code **and** an executed test that demonstrates the specific claim*.

| Pass | Strictly test-proven | Overstated | False |
|---|---:|---:|---:|
| 1 (seed 7) | 19 | 10 | 1 |
| 2 (seed 2026, after fixes) | 19 | 10 | 1 |

Every one of the 22 non-TRUE findings was resolved: a test was added where the behaviour existed (e.g. liveness, metric emission, entry point, audit record fields, schema-version rejection, simulation/explain side-effect freedom, subnormal/max-finite fuzz values), the code was fixed where the claim was false (zero/NaN locality multipliers are now rejected; project metadata completed), or the item was downgraded to `partial` with a note. **Read the `implemented` count accordingly:** by the reviewer's sampling, roughly one in three unsampled `implemented` items may rest on construction or indirect tests rather than a dedicated test — which is why every G04 "independent reproduction" item remains `external`.

## Defects found and fixed during the overhaul

1. Signing path spent ~70 % of decision time in a recursive finiteness check → native encoder with `allow_nan=False`.
2. Obligations were merged from every verdict → now only from sites the chosen option touches.
3. Config rollback followed by a forward activation could accept a revision below the highest ever activated → strict high-water mark.
4. "Reloadable" knobs were only read at construction → `_sync_config` applies them on the next decision.
5. Requests were parsed before authentication → authenticate first.
6. A revoked key could still sign; audit signing failure surfaced as a raw error → refused and mapped to `G14_AUDIT_UNAVAILABLE` (decision withheld).
7. Free-capacity shortfall was labelled `COMPUTE_INCOMPATIBLE` → `COMPUTE_UNAVAILABLE`.
8. A zero or NaN cross-site locality multiplier from GAP-03 was accepted (movement would look free) → rejected at the adapter and in the wire schema.
9. Liveness was a constant `true` → it now probes internal locks and the encoder, independent of dependencies.

## Open items by component (status `open`)

| Component | Items |
|---|---|
| P0-03 | D03 |
| P0-04 | A08, A10, E03 |
| P0-05 | D03 |
| P0-06 | A09, A10, D02, D03 |
| P0-07 | D03 |
| P0-08 | D01 |
| P0-09 | D02 |
| P0-12 | D02 |
| P1-13 | D03 |
| P1-14 | A09, D02, D03 |
| P1-15 | D03 |
| P1-17 | D02, D03 |
| P1-18 | D01 |
| P1-19 | A10, D01, D02, E04 |
| P1-20 | D03, E04 |
| P1-21 | A10, D02 |
| P1-22 | D02, D03, E02, E04 |
| P1-23 | B06, D03, G03 |
| P1-24 | D01 |
| P1-25 | A08, D01, D02, D03 |
| P1-26 | D01, D03 |
| P2-28 | D01, D03, E02 |
| P2-29 | B06, D01, D02, D03, E03 |
| P2-30 | A09, B05, D03, E02, E03, E04, G03 |
| P2-31 | D01, D03 |
| P2-32 | D03, E04 |
| P2-33 | A07, A08, A09, E03, G02 |
| P2-34 | A08, A09, B06, E03, E04 |
| P2-35 | A07, A08, B06, D03, E02, E03, G02 |
| P2-36 | A06, A07, A08, A10, B06, D02, D03, E02, E03, E04, G02, G03 |
| P2-37 | D03, E02 |
| P2-38 | D02, D03 |
| P2-39 | A08, D02, D03, E04 |
| P2-40 | D01, D02, D03 |

## External items (161)

Owners (every `A01`), independent reproduction (`G04`) and security sign-off (`G05`) for all 40 components; certified `pk_core` runs; live-estate integration; Windows and Python 3.12/3.13 runs; wheel/sdist build and signing; vulnerability scanning; human tabletop, game-day, restore and deprecation exercises.

## Known accepted risks (DESIGN §9)

R-1 HMAC symmetric trust · R-2 GIL-bound concurrency · R-3 per-process replay/explain state · R-4 DAG greedy beyond bound.
