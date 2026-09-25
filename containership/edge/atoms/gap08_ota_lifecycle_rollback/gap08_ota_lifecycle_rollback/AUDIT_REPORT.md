# GAP-08 v4.3.0 Audit & Build Report

**Date:** 2026-09-22  
**Input:** GAP-08 v4.2.0 + *GAP-08 v4.2.0 Missing-Components Professional Checklist* (40 components, 1,286 checkboxes)  
**Output:** GAP-08 v4.3.0

## Executive result

All 40 register components now exist as code, schema, tooling or governance artifacts inside the package, integrated by a new `controller.py` around the unchanged v4.2.0 state machine. 89 tests (86 run, 3 `pk_core` framework tests skipped because `pk_core` was not supplied) pass under `python` and `python -O`; a 1,000-node simulated rollout, an 80-rollout / 63-simulated-day soak with 41 controller takeovers, 5,000-iteration fuzzing and a single chaos campaign (lost acks, health outage, stale controller, store failover, audit-sink outage, reconnect storm, rollback failure) all pass.

The checklist is executed item by item in `docs/CHECKLIST_STATUS.{md,json}`:

| Status | Items |
|---|---|
| DONE (implemented + tested here) | 549 |
| DONE-SIM (tested against in-package simulations only) | 152 |
| PARTIAL (gap stated) | 426 |
| DOC (written, not yet reviewed/drilled) | 79 |
| OPEN (needs people, hardware, real services, long runs) | 80 |

**Production readiness: NOT READY.** Nothing in this pass can name owners, perform an independent security review, drill operators, certify hardware, run weeks-long soaks or talk to the real sibling services. Those are listed as open items with the exact action required.

## Defects found and fixed during the build

| Severity | Finding | Disposition |
|---|---|---|
| Critical | Rollback sent node commands before winning the state CAS; a concurrent gate commit left nodes on v1 while the durable record said v2 (reproduced ~40 % of runs by `test_concurrent_rollback_and_gate`). | Two-phase rollback (intent CAS → commands → outcome), refusal of other ops while an intent exists, `recover()` completes it. 60/60 clean reruns. |
| High | A delayed install could land after a concurrent rollback. | Node-side rollout tombstones (GAP-01 contract) + test `test_step_racing_rollback_never_leaves_bundle_behind`. |
| Medium | Two operations in one controller could both re-acquire a lapsed lease and fence each other (safe but spurious failures). | Per-controller lease lock. |
| Medium | `retry_deferred` returned before authorization when nothing was due (information leak + scope bypass). | Authorize first; covered by `Section11ScopedAuthorization`. |
| Low | Package import required `pk_core`. | Lazy import of the framework binding. |

## Verification performed

- `python3 -m compileall`: PASS.
- `tests/` via `unittest discover`: 89 tests, 86 pass, 3 skipped (pk_core absent) — also under `python -O`.
- `GAP08_FUZZ_ITERS=5000` property/fuzz suite: PASS.
- `tools/benchmark.py --sizes 50 200 1000`: complete rollouts, p95 step 0.93 s / gate 0.47 s at 1,000 nodes on the build host (reference file store; not a capacity claim).
- `tools/soak.py --cycles 80`: 70 complete, 4 rolled back, 6 rollback-incomplete → quarantine released with two-person approval; zero drift after every reconcile; audit sink verified (1,875 sealed entries).
- `tools/release_evidence.py build/verify`: evidence bound to 82+ file digests; bundle unsigned (no release key supplied).
- `tools/checklist_status.py --check`: 1,286 items, every evidence path exists.

## Not verified here

`tests/test_component.py` (pk_core conformance, 100 framework findings) could not run — `pk_core` was not in the upload. `component.py` was not modified beyond what its imports require; rerun it in the full framework.

## Shop notes

The GitHub Junkyard could not be reached from this session (folder access was not granted), so the shop ledger was neither consulted nor updated and no yard parts were pulled. Everything here is new code; see `THIRD-PARTY-NOTICES.md`.
