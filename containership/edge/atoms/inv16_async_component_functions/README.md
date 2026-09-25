# INV-16 - Async component functions

**Version:** 4.3.0 (see `CHANGELOG.md`; closure status in `docs/CLOSURE_LEDGER.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Async component functions are the guest-visible shape of the new ABI: a function declared async in the interface may return before its work is finished, and the caller decides whether to wait. The hard part is composition -- a sync caller of an async callee must still be correct, and re-entrancy must not corrupt the callee's state.

## Responsibility

Own the guest-facing async function surface: declaration, the sync/async call matrix, re-entrancy rules and the state machine each async function is compiled into.

## Owns

- Async function declaration and lifting
- The sync-caller/async-callee bridging rules
- Re-entrancy admission for an in-flight instance
- Per-call state machine storage
- Return-value delivery on completion

## Explicitly does not own

- Subtask handle mechanics
- Stream and completion payloads
- Scheduling
- Host I/O
- Interface syntax

## Non-goals

- Inferring async-ness at run time
- Owning the subtask table
- Making every function async
- Sharing state between in-flight calls

## Interfaces

- `declare` - PK_ASYNC_DECL/1 - build-time async-ness of a function
- `invoke` - PK_ASYNC_INVOKE/1 - a call carrying its own state machine
- `reentrancy` - PK_REENTRANCY/1 - admission decision for a re-entrant call

## Service-level objectives

- **state isolation** - zero bytes of call state shared between in-flight calls (error budget: no budget)
- **exactly once** - every completed call delivers its value exactly once (error budget: no budget)
- **bridge cost** - p99 sync-caller bridging under 5us (error budget: 1% may exceed)

## Layout (4.3.0)

| Path | Role |
|---|---|
| `runtime.py` | lifecycle model: admission, re-entrancy policy, bounded tombstones, call ids/generations, cancel reasons, events, trace |
| `bridge.py` | real sync-caller → async-callee bridge (ADR-0002) |
| `abi.py` | canonical, versioned return-value transport bound to a call id |
| `declare.py` | `PK_ASYNC_DECL/1` descriptor pipeline (INV-11 side) |
| `lowering.py` | reference async state-machine lowering with per-call frames |
| `observability.py` | metric catalogue, Prometheus export, structured event log, histograms |
| `preflight.py` | fail-closed environment/pk_core/topology preflight |
| `fixtures/` | SURROGATE INV-15/10/17/20 fixtures + interface golden files |
| `tests/` | 15 suites: races, stress, property/fuzz, faults, bridge, ABI, security, rollback/canary … |
| `bench/` | bridge-SLO benchmark, capacity benchmark, soak |
| `tools/` | lint, coverage gate, reproducible release, rollback, canary, evidence bundle + verifier |
| `docs/`, `ops/` | closure ledger, threat model, runbook, ADRs, compatibility, alerts, dashboard |
| `evidence/` | generated, hash-chained evidence bundle and `INV16_LOCAL_GATE.json` |

## Running it

```
cd inv16_async_component_functions/tests && python -m unittest discover -s . -t .   # all suites, no pk_core needed
python tools/lint.py && python tools/coverage_gate.py                              # stdlib gates
python bench/bridge_bench.py --gate                                                # bridge SLO gate
python tools/release.py build && python tools/release.py verify                    # reproducible artifacts
python tools/gen_evidence.py && python tools/verify_evidence.py                    # evidence bundle
python -m inv16_async_component_functions.preflight --require-pk-core             # certification preflight
python inv16_async_component_functions/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-16 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-16 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-16`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-16`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
