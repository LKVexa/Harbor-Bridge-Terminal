# PLN-03 - Distributed runtime plane

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** not present in this component archive; this is tracked explicitly in `MISSING_COMPONENTS.md`

The distributed runtime plane provides the sidecar-free building blocks an application uses at run time: state, messaging, secrets, and service invocation, behind stable APIs with pluggable backing infrastructure. Applications bind to capabilities, never to a broker or a database.

## Responsibility

Own the stable distributed-runtime API surface (state, messaging, secrets, invocation) and the adapter layer that binds each capability to concrete infrastructure without leaking the backend into the application.

## Owns

- The state, messaging, secrets, and invocation APIs
- Adapter registration and lifecycle
- At-least-once delivery and idempotency keys
- Capability-scoped access to each backing store
- Backend-independence of the API contract

## Explicitly does not own

- Backing store implementations
- Application business logic
- Placement of the runtime
- Transport-layer security primitives
- Durable workflow semantics

## Non-goals

- Implementing brokers or databases
- Guaranteeing exactly-once delivery
- Cross-tenant data access under any configuration
- Durable multi-step workflow execution

## Interfaces

- `invoke` - PK_INVOKE/1 - address another component by name, not by network location
- `messaging` - PK_MESSAGE/1 - publish and subscribe with idempotency keys
- `secrets` - PK_SECRET/1 - fetch a secret by capability-scoped reference
- `state` - PK_STATE/1 - get, set, delete, transact within a tenant namespace

## Service-level objectives

- **state latency** - p99 state get under 10ms against a local adapter (error budget: 1% may exceed)
- **capability enforcement** - zero calls served without a matching binding (error budget: no budget)
- **delivery** - at-least-once delivery for every accepted publish (error budget: 0.01% may require redelivery beyond the retry window)

## 4.3.0 governed runtime

Use `GovernedRuntime` (`plane.py`) in production paths; `DistributedRuntime` remains the dependency-free core and conformance oracle. See `docs/` for requirements, semantics, limits, threat model and operations, and `REMEDIATION_STATUS.json` for what is still open (owner assignments, ADR approvals, LICENSE, pk_core pin, adjacent-plane integration, wasmCloud/wRPC interop, MASTER.md).

```
python -m unittest discover -s tests -p "test_*.py" -t tests      # all suites
python tools/bench.py                                              # latency regression gate
python tools/release_evidence.py --out evidence                    # evidence bundle (set PK_EVIDENCE_KEY to seal)
```

## Running it

```
# Standalone operational tests (no pk_core required)
python -m unittest discover -s pln03_distributed_runtime_plane/tests -p "test_runtime.py" -v
python pln03_distributed_runtime_plane/audit_repository.py

# Full 100-item component conformance (requires the external pk_core package)
python pln03_distributed_runtime_plane/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run PLN-03 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-03 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

The reference Python runtime now implements state get/set/delete/transaction, messaging publish/subscribe, secret fetch, and component-name invocation. Inline values are capped at 1 MiB and state transactions at 128 operations. These limits are reference-runtime safeguards, not a substitute for the still-missing production quota/fairness/backpressure design.

For the second-pass production gap inventory, see `MISSING_COMPONENTS.md`.

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run PLN-03`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate PLN-03`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
