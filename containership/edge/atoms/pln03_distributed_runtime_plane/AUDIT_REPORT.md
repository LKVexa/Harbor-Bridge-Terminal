# PLN-03 v4.2.0 Audit, Fix, Hardening, and Second-Pass Report

## Scope

This pass inspected every file in the supplied `pln03_distributed_runtime_plane.zip`, parsed the 100-item checklist, reviewed the Python implementation against the declared contract, added standalone executable verification, corrected inaccurate evidence mappings, and performed a second static/behavioral audit.

## Version bump

`4.1.0` → `4.2.0`.

This is a backward-oriented hardening release of the reference implementation. It adds previously documented runtime methods, validation, bounded inline payload handling, thread-safe atomic operations, and audit artifacts without changing the four named interface families.

## Fixed defects

1. **Adapter availability mismatch:** `Adapter.accept()` now rejects operations while unavailable, matching the 4.1.0 changelog claim and the other adapter operations.
2. **Non-atomic publish/idempotency race:** publish now deduplicates, persists, and enqueues under one adapter lock. Concurrent duplicate publishers cannot both overwrite the message before dedupe resolves.
3. **Ambiguous dedupe key construction:** topic/idempotency combinations now use length-delimited components so `("a/b", "c")` cannot collide with `("a", "b/c")`.
4. **Missing documented state operations:** `state_delete()` and atomic `state_transact()` were added.
5. **Missing documented messaging operation:** `subscribe()` was added for the reference adapter.
6. **Missing documented secrets operation:** `secret_fetch()` was added with explicit not-found behavior.
7. **Missing documented invocation operation:** `invoke()` plus adapter target registration were added.
8. **Unbounded caller input:** names/keys, transaction length, and inline payload size are now validated; inline payloads are capped at 1 MiB.
9. **Weak error shape:** reference runtime exceptions now expose stable error-code attributes and structured detail dictionaries. A wire schema is still missing and is tracked separately.
10. **Testability coupled to `pk_core`:** operational runtime logic moved to `runtime.py`, which has no `pk_core` dependency; package import now remains usable without `pk_core`, while conformance symbols degrade explicitly.
11. **No race regression coverage:** standalone tests now include concurrent duplicate publishing with 32 threads.
12. **False evidence mapping:** implementation/resilience checklist overrides that previously labeled unrelated requirements satisfied were corrected to partial/satisfied findings that match the actual behavior.
13. **False packaging claim:** README no longer states that absent `MASTER.md` is included.
14. **Version drift:** VERSION, package version, README, changelog, and conformance version test were aligned to 4.2.0.

## Verification performed

- Python syntax compilation of all package and test modules: **PASS**.
- Standalone runtime unit suite: **11 tests PASS**.
- Full unittest discovery: **14 discovered; 11 PASS; 3 SKIPPED** because `pk_core` is not included/installed in the supplied archive.
- Optimized-mode standalone runtime suite (`python -O`): **PASS**.
- Checklist JSON parse/count/unique ordinal verification: **PASS (100 unique items, ordinals 1..100)**.
- Production-source bare-`assert` scan: **PASS**.
- Required runtime method surface check: **PASS** for state get/set/delete/transact, publish/subscribe, secret fetch, and invoke.

## Important audit correction

The historical 4.1.0 changelog says all 100 requirements were satisfied. This standalone archive does not contain enough implementation or evidence to substantiate that claim. v4.2.0 intentionally preserves known partial findings instead of masking them, and `MISSING_COMPONENTS.md` records the remaining gaps.

## Residual gaps

See `MISSING_COMPONENTS.md` and `MISSING_COMPONENTS.json`. The second pass identifies 56 distinct missing/incomplete production components, including capability-token enforcement, WIT/typed schemas, wasmCloud/wRPC/Wadm integration, actors/workflows scope resolution, resilience controls, observability, performance certification, full security controls, adjacent-plane tests, operational governance, `pk_core` reproducibility, and the absent `MASTER.md`.
