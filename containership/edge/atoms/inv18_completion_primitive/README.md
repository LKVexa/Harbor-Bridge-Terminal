# INV-18 - Completion primitive

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)
**Release status:** `NO_GO` — see `AUDIT_REPORT.md` and `conformance/RELEASE_EVIDENCE.json`

The completion primitive is the one-shot counterpart to a stream: exactly one value, delivered once, to exactly one receiver. Having it as its own type rather than a stream of length one means the compiler knows there is no second value coming, so the receiver needs no loop and the writer cannot accidentally send twice.

## Responsibility

Own one-shot value delivery: a future handle that resolves at most once, an explicit error resolution, and the refusal of a second resolution or a second receiver.

## Owns

- Future handle allocation and typing
- At-most-once resolution
- Error resolution as a first-class outcome
- Single-receiver enforcement
- Abandonment detection when the writer is dropped unresolved

## Explicitly does not own

- Many-valued flow
- The subtask table
- Retry policy
- Transport
- Payload meaning

## Non-goals

- Carrying many values
- Retrying the producer
- Broadcasting to several receivers
- Allowing a resolution to be overwritten

## Interfaces

- `abandon` - PK_FUTURE_ABANDON/1 - writer dropped without resolving
- `future` - PK_FUTURE/1 - a typed one-shot handle
- `resolve` - PK_FUTURE_RESOLVE/1 - value or error resolution

Machine-readable schemas: `schemas/`; structured errors `PK_FUTURE_ERROR/1`; status `PK_FUTURE_STATUS/1`.

## Service-level objectives

- **at most once** - zero futures resolved twice (error budget: no budget)
- **no orphans** - every abandoned future raises on the receiver (error budget: no budget)
- **resolution cost** - p99 resolution delivery under 1us within an instance (error budget: 1% may exceed) — **not met in CPython**; revised objective PROPOSED (W-C062, docs/OPERATIONS.md)

## Package map

| Layer | Files |
|---|---|
| primitive (stdlib only) | `future.py`, `errors.py` |
| governed runtime | `runtime.py` (capabilities, quotas, disable, health), `config.py`, `telemetry.py`, `status.py`, `slo.py`, `alerts.py` |
| remote boundary | `wire.py`, `auth.py`, `adapters.py`, `retry.py` |
| adjacent layers (doubles) | `adjacent.py` |
| verification | `tests/` (tagged `REQ:`), `fixtures/`, `fault.py`, `bench.py`, `fixtures_runner.py`, `testrunner.py` |
| release | `certify.py` (RTM + C100 gate), `bootstrap.py`, `tools_verify.py`, `tools/`, `SHA256SUMS` |
| pk_core audit integration | `component.py`, `contract.py` (need `pk_core`, loaded lazily) |
| governance | `governance/` (owners, waivers, reviews, accepted conditions), `CODEOWNERS`, `REQUIREMENTS.json` |
| specs | `docs/adr/ADR-001…`, `docs/ARCHITECTURE.md`, `INTERFACES.md`, `SECURITY.md`, `RESILIENCE.md`, `PERFORMANCE.md`, `OBSERVABILITY.md`, `OPERATIONS.md` |

## Using it

```python
from inv18_completion_primitive import Runtime, Abandoned
rt = Runtime({"environment": "dev"})
writer, reader = rt.create(int, tenant="acme")   # capabilities, not raw futures
rt.resolve(writer, 42)
rt.take_wait(reader, timeout=5.0)                # ('ok', 42); a second take raises AlreadyTaken
```

The bare `Future` (no runtime) remains available and API-compatible with 4.2.0.

## Running it

From the directory that contains the package:

```
python -m inv18_completion_primitive bootstrap        # day-0 clean bootstrap report
python inv18_completion_primitive/tools/run_tests.py  # full suite, machine-readable results
python -m inv18_completion_primitive conformance      # wire fixtures
python -m inv18_completion_primitive status | explain
python -m inv18_completion_primitive gate             # C100 exit gate: exit 0 GO / 10 CONDITIONAL_GO / 20 NO_GO
python inv18_completion_primitive/tools/verify.py inv18_completion_primitive
```

pk_core commands (require `pk_core` on the path, `PK_CORE_PATH` for the integration test):

```
python -m pk_core run INV-18 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-18 --out conformance/PK_GATE_RESULTS.json
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

Formal, CI-executed runbooks are in `docs/OPERATIONS.md` (RB-D0, RB-D1, RB-D2, INC-1..4).
Ownership and escalation: `governance/OWNERS.json`. Traceability: `conformance/RTM.md`.

Rollback is the previous sealed evidence head; emergency disable is
`Runtime.disable(admin_cap, mode="freeze")` or removal of the component from the registry
package, which the gate reports as a reduced element count rather than a silent pass.
