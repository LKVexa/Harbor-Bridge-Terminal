# INV-21 - Local service chaining

**Version:** 4.3.0 (see `CHANGELOG.md`, `AUDIT_REPORT_4.3.0.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Local service chaining is what makes the component model pay off operationally: when component A calls component B and both are on the same host, the call never becomes a network request. It becomes a direct invocation, with the same interface, the same capability checks and the same observability -- the topology changes, the semantics do not.

## Responsibility

Own the local call path between co-resident components: resolution, the decision to chain locally or fall back to the network, loop prevention, depth bounding and preservation of identity and trace context across the hop.

## Owns

- Co-residency detection and local dispatch
- Chain depth and cycle bounding
- Identity and trace propagation across a local hop
- Fallback to the network path when the callee is remote
- Per-hop capability re-checking

## Explicitly does not own

- Placement decisions
- The network transport
- Interface definitions
- Service discovery beyond the local host
- Business logic

## Non-goals

- Deciding placement
- Implementing the network transport
- Changing call semantics for local hops
- Allowing cross-tenant local calls

## Interfaces

- `chain` - PK_LOCAL_CHAIN/1 - a call routed locally or remotely
- `depth` - PK_CHAIN_DEPTH/1 - the current chain depth and its bound
- `residency` - PK_RESIDENCY/1 - which components share this host

## Service-level objectives

- **semantic identity** - local and remote calls produce identical results (error budget: no budget)
- **tenant containment** - zero local calls across a tenant boundary (error budget: no budget)
- **local hop cost** - p99 local dispatch under 20us versus milliseconds over the network (error budget: 1% may exceed)

## Running it

```
python inv21_local_service_chaining/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-21 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-21 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-21`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-21`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.


## 4.2 runtime hardening

The local path now uses a synchronized, revisioned residency table; immutable placement records; bounded trace/decision telemetry; stable machine-readable chain exceptions; an injectable per-hop capability checker; and an injectable remote-dispatch handoff. A standalone runtime suite exercises these primitives even when the sibling `pk_core` package is unavailable during an isolated audit.

## 4.3.0 runtime layout (stdlib-only)

| Module | Role |
|---|---|
| `chain.py` | `Chainer.invoke` / `ainvoke` (production, authenticated) and 4.x `call` (development only) |
| `context.py` | `IdentityVerifier`, `Principal`, `CallContext` (PK_CALL_CONTEXT/1), `Deadline`, `CancelToken` |
| `policy.py` | PK_CAPABILITY/1 decision contract, `GuardedProvider` (fail closed, bounded cache) |
| `residency.py` | PK_RESIDENCY/1 table with leases, epochs, watchers, snapshot/restore/reconcile |
| `admission.py` | admission control, per-tenant rate limits, circuit breaker, retry policy |
| `transport.py` | PK_LOCAL_CHAIN/1 wire, `HttpJsonTransport`, `LoopbackTransport`, `ChainEndpoint`, `/healthz /readyz /metrics` |
| `errors.py` | PK_CHAIN_ERROR/1 stable taxonomy and normalisation |
| `audit.py` | PK_CHAIN_AUDIT/1 tamper-evident HMAC hash chain |
| `telemetry.py` | bounded metrics (Prometheus text), decision ledger, explain view, pseudonymisation |
| `config.py`, `lifecycle.py`, `rollout.py` | PK_CHAIN_CONFIG/1, atomic activation/rollback, state machine, canary evaluation |
| `component.py`, `contract.py` | pk_core adapter (requires pk_core) |

Run the suite: `cd inv21_local_service_chaining && python -m unittest discover -s tests -t tests`
(fails while pk_core is absent — by design; developers may set `INV21_ALLOW_PK_CORE_SKIP=1`).
Release gate: `python -m inv21_local_service_chaining.tools.release_gate` → `evidence/gate_result.json`.
Docs: `docs/` (design, threat model, operations, incident, capacity, compatibility, equivalence, privacy, patching, reviews, ADRs, traceability).
