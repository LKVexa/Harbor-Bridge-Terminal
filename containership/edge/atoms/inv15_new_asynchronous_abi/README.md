# INV-15 - New asynchronous ABI

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`  
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The new asynchronous ABI lets a component wait without pinning a guest stack, thread, or core. A call either completes synchronously or returns an opaque subtask handle. Readiness remains authoritative in a host-owned waitable table, and outstanding work is bounded per instance.

## v4.3.0 — checklist execution

`host.AsyncHost` implements the 72-component checklist as a stdlib-only reference host; `certification/COMPONENT_STATUS.md` states, box by box, what is evidenced, partial, blocked or not done. Run the whole gate with `python inv15_new_asynchronous_abi/tools/certify.py` (or `sh inv15_new_asynchronous_abi/ci.sh`) from the folder containing the package.

This is still **not a production host ABI**: no production backend, no second independent runtime, no signing, no owners or reviewers.

## v4.2.0 hardening summary

The runtime reference model now lives in dependency-free `abi.py`; the `pk_core` checklist integration remains in `component.py`.

- Opaque subtask handles use a fresh 128-bit random token per handle plus a diagnostic sequence number.
- Pending subtasks cannot be consumed; `take()` raises `SubtaskNotReady` until completion.
- `None` is now a valid synchronous return value.
- `wait()` consumes iterables exactly once, supports generators correctly, deduplicates set members, and bounds request size.
- The live waitable table is thread-safe and exposed only through a read-only snapshot.
- Consumed/cancelled handles are retired from the live table; bounded tombstones detect recent use-after-consume without unbounded memory growth.
- Single-handle cancellation and caller-loss cleanup release pending work and already-ready unread results.
- Cancellation reason cardinality is bounded.
- The runtime ABI can be imported and tested without `pk_core`; certification integration is lazy-loaded.

See `AUDIT_REPORT.md` for the audit trail and `MISSING_COMPONENTS.md` for remaining production components.

## Responsibility

Own the asynchronous calling convention: opaque subtask handles, the waitable-set primitive, cancellation propagation, backpressure, and the guarantee that no guest stack is blocked while a call is outstanding.

## Owns

- Opaque subtask handle allocation, validation, retirement, and bounded tombstones
- Host-owned waitable sets and readiness reporting
- Per-handle and caller-loss cancellation propagation
- Backpressure when an instance exceeds its outstanding-call budget
- Thread-safe reference state transitions
- The guarantee that waiting consumes no guest stack

## Explicitly does not own

- The interface definitions being called
- Stream and completion payload semantics
- Host I/O implementations
- Scheduling policy
- Language bindings

## Interfaces

- `call` - `PK_ASYNC_CALL/1` - returns a value or an opaque subtask handle
- `wait` - `PK_WAITABLE_SET/1` - returns ready members of a bounded handle set
- `cancel` - `PK_SUBTASK_CANCEL/1` - cancels/abandons an outstanding handle

## Runtime state model

Live subtasks move from `pending` to `ready`, then leave the live table through `take()`, `cancel()`, or `cancel_all()`. A bounded tombstone cache records recently retired handles for deterministic use-after-consume diagnostics while preventing historical state from growing without bound.

## Running it

From the folder containing `inv15_new_asynchronous_abi`:

```text
python inv15_new_asynchronous_abi/tests/test_abi.py
python -O inv15_new_asynchronous_abi/tests/test_abi.py
python inv15_new_asynchronous_abi/tests/test_component.py
```

The runtime tests require only the Python standard library. The `component.py` certification checks require the external `pk_core` framework; set `PK_CORE_PATH` when it is stored elsewhere.

When `pk_core` is available:

```text
python -m pk_core list
python -m pk_core run INV-15 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-15 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** run the dependency-free ABI suite, then execute the `pk_core` evidence run and archive the evidence head.
- **Day 1:** execute the production gate; block rollout on `NO_GO` and explicitly record any accepted conditional gates.
- **Day 2:** rerun ABI tests, compatibility tests, and the certification gate on every implementation, contract, or configuration change.

Rollback remains the previous sealed artifact/evidence head. Emergency disable removes the component from the registry package; it must not silently convert absence into a passing result.
