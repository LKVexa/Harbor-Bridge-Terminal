# INV-57 — Durable execution

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-57 defines durable workflow replay: completed activities are reconstructed from an append-only history instead of being executed again after a restart. The workflow code must remain deterministic with respect to that history; divergent replay is rejected before new activity code runs.

## What this repository contains (v4.3.0)

| Module | Role | Checklist |
|---|---|---|
| `durable.py` | stdlib replay engine: started/completed/failed journal, tagged encoding, SHA-256 chain, in-doubt halt, divergence detection. v4.3.0 makes replay O(n) (incremental validation, no per-step history copy) and routes every malformed payload to `HistoryCorruption`. | core |
| `sqlite_store.py` | persistent reference backend: conditional append, lease/epoch fencing inside the append transaction, chain check on read, quarantine, lifecycle table, effect records, online backup and verified restore, crash-point test hook | SG-01, SG-03, SG-09, MC-40, MC-61 |
| `identity.py` | immutable composite workflow identity with an injective key and principal binding | SG-02 |
| `lifecycle.py` | closed 11-state lifecycle machine with idempotent controls | MC-05, SG-08 |
| `effects.py` | external-effect protocol: deterministic effect ids, prepared-before-dispatch, receipt reconciliation | SG-04 |
| `errors.py` | machine-readable error model (stable codes, retryability, safe-detail flag) | MC-14 |
| `config.py` | typed config schema, overlays, hash-chained provenance ledger, atomic activation, rollback | MC-21..25 |
| `resilience.py` | bounded jittered retry (after_backoff only), circuit breaker, per-tenant admission control | MC-38, MC-07 |
| `telemetry.py` | metrics (Prometheus text), allowlisted JSON logs with redaction, W3C trace ids | MC-48, MC-49 |
| `status.py` | liveness/readiness/degraded/frozen status with cached dependency probes | MC-47 |
| `acceptance.py` | fail-closed production exit gate and acceptance manifest | MC-57, MC-65, RG-08 |
| `schemas/`, `fixtures/` | JSON Schemas generated from code; golden history fixture | MC-10, MC-17 |
| `docs/` | ARCHITECTURE (ADR, SHALL reqs, NFRs, versioning, threat model: PROPOSED) and OPERATIONS runbooks (draft) | MC-02..09, MC-28, MC-62 |
| `STATUS_REGISTER.json` | status, evidence, tests and blockers for all 82 remediation components | all |
| `component.py` / `contract.py` | adapter/contract for the external `pk_core` framework (still unpinned) | RG-01 |

`MASTER.md` is not present in any supplied archive. It is treated as absent and non-authoritative, and nothing reconstructs it.

Operator CLI: `python -m inv57_durable_execution {status,gate,errors,lifecycle,config-validate}`.
Full local CI: `sh ci.sh` (compile, schema drift, tests, `-O` tests, benchmark regression, reproducible wheel, clean-venv install/uninstall test, gate).

**Production status: NO_GO.** `python -m inv57_durable_execution gate` explains why. See `REMEDIATION_REPORT.md`.

## Core replay invariants

1. A new activity receives a durable `started` event before user code runs.
2. A successful activity result is deterministically encoded and appended as `completed` before the workflow proceeds.
3. A completed activity replays from history and does not run its function again.
4. A `started` activity without a durable outcome is treated as **in doubt**. Automatic re-execution is refused because the external effect may already have occurred.
5. Workflow code that changes the activity order, identity, or optional fingerprint is rejected as non-deterministic before new effects run.
6. The history is bounded and hash chained; malformed or tampered serialized history is rejected.
7. The same `Worker` instance cannot execute two workflows concurrently.

8. With `SQLiteHistoryStore`, an append commits only while the writer holds the current, unexpired lease epoch and the append extends the exact tail. A stale worker can run code but cannot commit.

These semantics do **not** make a production exactly-once distributed system on their own. The INV-50 state and INV-53 messaging bindings, real effect providers and deployment are still BLOCKED. `STATUS_REGISTER.json` lists every blocker.

## Example

```python
from inv57_durable_execution import ActivityInDoubt, Crash, Worker

worker = Worker()


def workflow(w):
    account = w.activity("lookup", lambda: {"id": "acct-1"})
    receipt = w.activity(
        "charge",
        lambda: "receipt-1",
        activity_id="charge:order-42",
        fingerprint="order-42:$19.00:v1",
    )
    return account, receipt

result = worker.run(workflow)
```

Use stable `activity_id` and `fingerprint` values when the activity name alone is not enough to describe replay compatibility.

## Testing

From the directory that contains `inv57_durable_execution`:

```text
python -m unittest discover -s inv57_durable_execution/tests -t . -v
python -O inv57_durable_execution/tools/run_tests.py      # writes test-report.json for the gate
```

The core suite is stdlib-only. For the external conformance adapter, make `pk_core` importable (or set `PK_CORE_PATH`) and then run the same discovery command.

## `pk_core` integration

When `pk_core` is installed in the surrounding project, the intended commands remain:

```text
python -m pk_core list
python -m pk_core run INV-57 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-57 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

The supplied standalone ZIP does not include or pin `pk_core`; therefore a framework-level 100-item production gate cannot be reproduced from this archive alone. The self-contained core tests are the independently reproducible validation surface in this package.

## Contract responsibility

Own durable workflows: event-sourced history, deterministic replay, once-only replay behavior for completed activities, conservative handling of ambiguous in-flight effects, and detection of non-deterministic workflow code.

### Owns

- Workflow history semantics
- Deterministic replay
- Completed-activity replay without re-execution
- Non-determinism detection
- Restart/resume semantics

### Does not own

- Activity business logic
- A production history storage backend
- Timer infrastructure
- Worker scheduling
- Messaging transport
- Distributed fencing/leases
- External side-effect transaction protocols

## Production targets in the contract

The contract declares targets for once-only effects, deterministic replay, and p99 replay speed. They are **targets**, not benchmark evidence. This repository does not yet contain the production performance, fleet, security, integration, or disaster-test evidence necessary to certify those targets. See `AUDIT_REPORT.md` and `TRACEABILITY.json`.

## Day 0 / Day 1 / Day 2 intent

- **Day 0:** run the self-contained unit suite; if `pk_core` is available, generate the initial evidence ledger.
- **Day 1:** run the external production gate and block rollout on unresolved findings.
- **Day 2:** re-run unit, integration, security, performance, and conformance gates on every change; verify history/evidence continuity and rehearse rollback/recovery.

The full operational runbooks, compatibility matrix, incident procedures, deployment automation, and acceptance evidence are still missing and are explicitly enumerated in the audit report.
