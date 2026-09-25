# INV-14 - Previous asynchronous model

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The previous asynchronous model is the poll-based one: a component hands the host a list of pollables and blocks until one is ready. It works, it is simple, and it does not compose -- which is exactly why the new ABI exists. This element keeps it running honestly while it is still deployed, and states what it cannot do.

## Responsibility

Own the legacy poll-based async surface for components still using it: block on a pollable set with a bounded timeout, guarantee no lost readiness, and mark the model deprecated so nothing new is written against it.

## Owns

- The pollable set and its latched readiness semantics
- Real bounded waiting with an explicit timeout and a hard wall-clock ceiling
- Lost-wakeup prevention using durable waiter registration
- Per-instance ownership enforcement and finite poll-set capacity
- Structured poll errors and stable ready indexes/names
- Deprecation status, migration target, and bounded in-memory counters
- Refusal to compose a pollable across component boundaries

## Explicitly does not own

- The new asynchronous ABI
- Stream and future primitives
- Host I/O implementations
- Scheduling
- Placement

## Non-goals

- Composing async across components
- Being the model new code is written against
- Replacing the new ABI
- Unbounded blocking

## Interfaces

- `poll` - PK_POLL/1 - bounded wait on a finite pollable set; returns ready names and indexes
- `pollable` - PK_POLLABLE/1 - a latched readiness handle owned by one instance
- `poll_error` - PK_POLL_ERROR/1 - machine-readable validation/boundary refusal details
- `poll_metrics` - PK_POLL_METRICS/1 - bounded in-memory counters for telemetry export

## Service-level objectives

- **no lost wakeups** - zero readiness signals dropped across a poll boundary (error budget: no budget)
- **bounded blocking** - zero polls blocking past their timeout (error budget: no budget)
- **migration visibility** - every use reports the deprecation and the migration target (error budget: no budget)

## Running it

```
python inv14_previous_asynchronous_model/tests/test_polling.py     # always runs; stdlib only
python -O inv14_previous_asynchronous_model/tests/test_polling.py  # optimized-mode parity
python inv14_previous_asynchronous_model/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python inv14_previous_asynchronous_model/verify_release.py          # fail-closed release gate; requires pk_core
python -m pk_core list
python -m pk_core run INV-14 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-14 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-14`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-14`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.


## v4.2.0 hardening notes

The retained reference implementation now blocks for real instead of immediately
returning a synthetic timeout. `Pollable.signal()` latches readiness, registers a
durable wake event before sleeping, and cannot lose a wake that races the poll
boundary. Poll requests fail closed on malformed members, foreign owners,
duplicate handles/names, over-capacity sets, invalid timeouts, and durations over
60 seconds. Results retain the legacy `ready` names and add `ready_indexes` so
identity is unambiguous.

`tests/test_polling.py` is intentionally independent of `pk_core`; this prevents a
missing framework install from making the entire behavioural test run appear green
through skips. Full 100-item conformance still requires `pk_core` and remains a
separate gate.

See `AUDIT_REPORT.md` for the repair record and `MISSING_COMPONENTS.md` for the
remaining productionization gaps.


## v4.3.0 production control surface

v4.3.0 implements the 35 components from `docs/INV14_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md` around the
unchanged v4.2.0 primitive. Start at `service.LegacyPollService` (the front door), `docs/COMPONENT_SPECS.md`
(what each component guarantees) and `evidence/CHECKLIST_STATUS.md` (the state of all 1,593 controls).

```
python3 -B verify_release.py            # 0 = certified, 1 = defect, 2 = BLOCKED (external gates listed)
python3 -B tools/run_evidence.py        # regenerate evidence/ from a full run
python3 -B tools/runbook.py --state DIR status|disable|rollback|verify-audit
python3 -B tools/sign.py verify --require-trusted
python3 -B core_probe.py pin --path <pk_core> --version X.Y.Z --source <index>   # once pk_core is supplied
```

Runtime code remains standard-library only. `cryptography` (or the `openssl` CLI) is needed only to
sign/verify releases. Always run with `-B` inside a sealed tree: bytecode caches are excluded from the
manifest but should not be written into release copies.
