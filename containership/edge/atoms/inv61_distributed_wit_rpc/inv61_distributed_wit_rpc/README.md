# INV-61 - Distributed WIT RPC

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`

Distributed WIT RPC carries typed interface calls between components on different hosts. Each frame names the interface, version and function and carries a fingerprint of the caller's signature; the receiver checks that fingerprint against its own before decoding a byte, so two sides that drifted apart fail with a clear error instead of misreading each other's arguments.

## Responsibility

Own cross-host typed invocation: frame format, signature fingerprints, receiver-side compatibility checks, typed error returns and deadlines.

## Owns

- RPC frame format
- Signature fingerprinting
- Receiver-side compatibility check
- Typed error returns
- Per-call deadlines

## Explicitly does not own

_Contract text unchanged from 4.2.0. Since 4.3.0 the package ships a default AES-GCM record layer (docs/ADR-0001, PROPOSED); control-class sealing stays with INV-36 and the ownership line awaits the owner's decision._

- Interface definitions
- Transport encryption
- Service discovery
- Component logic
- Load balancing

## Non-goals

- Defining interfaces
- Encrypting transport
- Discovering services

## Interfaces

- `deadline` - PK_WRPC_DEADLINE/1 - absolute call deadline
- `error` - PK_WRPC_ERROR/1 - a typed error result
- `frame` - PK_WRPC_FRAME/1 - interface, version, function, fingerprint, args (in-process `rpc.py`)
- `frame` - PK_WRPC_FRAME/2 - binary wire envelope + canonical WIT value encoding (`wrpc/codec.py`)

## Service-level objectives

- **no misreads** - zero frames decoded against a mismatched signature (error budget: no budget)
- **deadlines** - zero calls outliving their deadline (error budget: no budget)
- **overhead** - p99 framing overhead under 50us (error budget: 1% may exceed)

## Running it

```
pip install -r requirements.lock                       # cryptography (AES-GCM record layer)
python -B -m unittest discover -s tests -v             # 123 tests; 4 skip without pk_core
python -B tools/run_gate_tests.py                      # release gate: fails on any skip
INV61_PSK=<64 hex> python -B tools/serve.py --peer svc-a --tenant t1 --key-id k1
python -B tools/bench.py --out evidence/bench.json
python -B tools/soak.py --seconds 60 --out evidence/soak.json
python -B tools/sbom.py --out evidence/sbom.cdx.json --sums SHA256SUMS
python -B tools/checklist_status.py --check
python -m pk_core gate INV-61 --out conformance/PK_GATE_RESULTS.json   # needs pk_core (BLOCKED, M01)
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-61`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-61`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.

## What 4.3.0 adds (M01-M32 completion pass)

`wrpc/` is a cross-host implementation built on the 4.2.0 reference codec: a bounded WIT parser
and canonical binary codec (`wit.py`, `codec.py`), a PSK mutual-auth handshake with downgrade
protection and an AES-256-GCM record layer with replay rejection (`security.py`), default-deny
authorization, idempotency, retry budgets, admission control, circuit breaking and fenced leases
(`controls.py`), layered config with provenance, a hash-chained audit log, Prometheus metrics,
redacting JSON logs, W3C trace context, time-boxed health checks and a restart journal (`ops.py`),
all joined in a TCP node/client (`node.py`). Evidence: `tests/` (123 tests), `evidence/`
(bench, soak, SBOM), `docs/` (requirements + traceability, threat model, ADR, operations,
telemetry policy, support matrix, dependencies, release).

The honest status of all 1,345 completion-checklist items is in `CHECKLIST_STATUS.json` and
`CHECKLIST_STATUS.md`. **Production use is not authorised**: `pk_core` (M01) and `MASTER.md`
(M02) are absent, the owner/approver (M22) is unassigned, the CI matrix (M27) has not run, and no
independent security review has happened. See `docs/OPERATIONS.md` §8.

The historical README referenced `MASTER.md`, which was not present in the supplied archive; it
has not been fabricated (`docs/MASTER_SOURCE.md`).
