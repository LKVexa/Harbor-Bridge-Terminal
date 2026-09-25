# INV-15 v4.2.0 Audit Report

**Artifact audited:** `inv15_new_asynchronous_abi.zip`  
**Input SHA-256:** `36d786f38559e1ecf2e2fb90e74de555614f32927f711289585cbfb722da43cd`  
**Previous version:** 4.1.0  
**Hardened version:** 4.2.0  
**Audit date:** 2026-09-22

## Executive result

The archive was structurally sound and syntactically valid, but the v4.1.0 reference runtime still contained security, lifecycle, iterator, resource-retention, and concurrency defects that were material to an asynchronous ABI. The runtime model was refactored and hardened in v4.2.0, with 12 dependency-free regression tests passing in both normal and optimized Python execution.

Full production certification remains dependent on the external `pk_core` framework and on the missing host/runtime integration components listed in `MISSING_COMPONENTS.md`.

## Findings and disposition

| ID | Severity | Finding | Disposition in v4.2.0 |
|---|---|---|---|
| A-01 | Critical | Integer handles were only instance-local by table lookup. If two instances both minted handle `1`, a numeric handle alone had no globally unique authority semantics. | Replaced with opaque per-subtask 128-bit random tokens plus diagnostic sequence numbers; cross-instance collision tests added. |
| A-02 | Critical | A holder able to infer local integer sequences could synthesize other live handles within the same instance. | Each subtask now receives independent random authority; one handle no longer reveals another handle's authority token. |
| A-03 | High | `take()` consumed a pending task and returned its default `None` value, destroying the eventual result. | Added `SubtaskNotReady`; pending rows remain live and unconsumed. |
| A-04 | High | `wait()` iterated `handles` once for validation and a second time for readiness, so generators/one-shot iterators always returned an empty ready set. | Wait input is consumed exactly once, bounded, then evaluated atomically against the host table. |
| A-05 | High | Consumed/cancelled subtasks remained in `table` forever; the outstanding budget was bounded but historical memory was not. | Live rows are retired immediately; recent tombstones are bounded by `tombstone_limit`. |
| A-06 | High | `cancel_all()` ignored ready-but-unread rows, allowing caller disappearance to retain host state indefinitely. | Caller-loss cleanup retires both pending and ready-unread rows; pending cancellations and abandoned-ready rows are accounted separately. |
| A-07 | High | The declared per-subtask cancel interface had no corresponding single-handle runtime operation. | Added `cancel(handle, reason)` with deterministic row release and propagation status. |
| A-08 | High | State transitions were not synchronized; concurrent allocation/completion/wait/cancel could race. | Added `RLock` protection and a 64-thread concurrent allocation regression test. |
| A-09 | Medium | `call(immediate=None)` could not represent synchronous `None`, because `None` doubled as the “no immediate result” sentinel. | Added a private sentinel object; `None` is now a valid synchronous value. |
| A-10 | Medium | Wait requests had no explicit size bound and duplicate members could amplify work. | Requests are capped at the live-subtask budget and duplicate members collapse to set semantics. |
| A-11 | Medium | The live host table was directly mutable through the public dataclass field. | Internalized `_table`; callers receive a read-only mapping snapshot containing immutable subtask records. |
| A-12 | Medium | Cancellation reason strings could create unbounded metric-cardinality growth. | Reason keys are length-bounded and limited to 32 distinct keys plus `__other__`. |
| A-13 | Medium | Constructor validation occurred only during async `call()`, allowing invalid instances to exist until later. | Instance, budget, and tombstone limits are validated in `__post_init__`. |
| A-14 | Medium | Runtime import was unnecessarily coupled to `pk_core`, preventing isolated testing or embedding. | Moved the runtime to `abi.py` and lazy-loaded certification-only symbols. |
| A-15 | Low | User-supplied wait iterators were consumed while holding the host lock in the first hardening draft, allowing arbitrary iterator code to extend lock hold time. | Final v4.2.0 consumes the bounded iterator outside the host-table lock, then validates the captured handles under lock. |

## Files changed or added

- `abi.py` — new dependency-free hardened runtime state machine.
- `component.py` — reduced to certification integration and behavioral evidence.
- `__init__.py` — v4.2.0 exports plus lazy `pk_core` integration imports.
- `contract.py` — tightened handle, memory, and caller-loss invariants.
- `tests/test_abi.py` — new runtime regression suite.
- `tests/test_component.py` — updated v4.2.0 metadata and conditional certification integration.
- `README.md` — revised architecture, usage, and lifecycle documentation.
- `CHANGELOG.md` — v4.2.0 release record.
- `MISSING_COMPONENTS.md` — production gap inventory.
- `MANIFEST.sha256` — integrity hashes for package files.

## Validation performed

1. Python bytecode compilation with `python -m compileall` — PASS.
2. Dependency-free runtime suite — 12 tests PASS.
3. Optimized mode (`python -O`) runtime suite — 12 tests PASS.
4. Certification test file — metadata PASS; `pk_core`-dependent tests correctly SKIPPED because `pk_core` is unavailable in the supplied archive/runtime.
5. Source scan — no bare production `assert` statements, dynamic `eval`/`exec`, `shell=True`, `os.system`, or pickle deserialization in runtime code.
6. Archive contents — no generated `__pycache__` or `.pyc` files retained in the final package.

## Residual risk

v4.2.0 is a hardened reference model, not yet a complete production host ABI. It still lacks a canonical wire/WIT schema, real host scheduler wakeup integration, timeout/deadline semantics, machine-readable failure envelopes, production telemetry exporters, fuzz/race/soak certification, multi-runtime compatibility evidence, artifact signing/SBOM, and deployment/incident automation. Those gaps are enumerated in `MISSING_COMPONENTS.md`.

---

# v4.3.0 addendum — component-checklist execution (2026-09-22)

**Input:** `inv15_new_asynchronous_abi_v4.2.0_hardened.zip` (MANIFEST verified clean before work began) and `inv15_new_asynchronous_abi_v4.2.0_COMPONENT_CHECKLISTS.md` (72 components, 1,584 component boxes + 15 Definition-of-Done boxes).

**Result:** every one of the 1,599 boxes has a recorded status, reason and evidence pointer in `certification/CHECKLIST_STATUS.json` (see `COMPONENT_STATUS.md` for the per-component table). No box is ticked `[x]`: the checklist reserves that for verified evidence under an owner and reviewer, and none exist. Release verdict: **NOT RELEASABLE**.

`abi.py`, `component.py`, `contract.py`, `MASTER.md`, `CHECKLIST.json` and `MISSING_COMPONENTS.md` are byte-identical to v4.2.0. The two defects fixed and the three flagged-but-open defects are listed in `CHANGELOG.md`.

**Chop-shop note:** the yard copy reached for this job (`C:\Users\russe\OneDrive\Desktop\GitHub Junkyard` on moneymoneymoney) has no `_YARDOFFICE`, so there was no ledger recall, map query or ledger log. No donor code was pulled; everything is new, stdlib-only, and needs no third-party notice.
