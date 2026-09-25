# GAP-01 - Edge Node Supervisor

**Version:** 5.0.0 (see `CHANGELOG.md`)
**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`

The edge node supervisor runtime model is the single local authority on a node: it owns the node's lifecycle state machine, drains workloads before the node stops accepting them, and keeps the node honest when the control plane is unreachable. Nothing else on the node may declare it healthy.

## Responsibility

Own the node lifecycle state machine -- joining, ready, draining, cordoned, stopped -- enforce legal transitions, and drain admitted workloads before a node leaves service.

## Owns

- The node lifecycle state machine and its legal transitions
- Local health aggregation for the node
- Workload drain ordering and completion
- Cordon and uncordon
- Local supervision when the control plane is unreachable

## Explicitly does not own

- Placement decisions
- Isolation enforcement
- Hardware capability discovery
- Control-plane membership
- Workload business logic

## Non-goals

- Deciding where drained workloads go
- Provisioning or decommissioning hardware
- Acting as a control-plane member
- Declaring a node healthy on missing evidence

## Interfaces

- `drain` - PK_DRAIN/1 - drain progress per workload with deadlines
- `health` - PK_NODE_HEALTH/1 - aggregated local health and its contributing signals
- `lifecycle` - PK_NODE_LIFECYCLE/1 - transition requests and the resulting node state

## Service-level objectives

- **transition legality** - zero illegal lifecycle transitions applied (error budget: no budget)
- **drain completeness** - zero nodes reporting stopped with resident workloads (error budget: no budget)
- **cordon latency** - placements stop within one scheduling interval of cordon (error budget: 1% may see one extra placement)

## Running it

```
python gap01_edge_node_supervisor/verify.py                 # compile + every suite, no network, no pk_core
python -m gap01_edge_node_supervisor.bootstrap --node n1 \
    --state-dir /var/lib/gap01 --socket /run/gap01/control.sock \
    --caller-key control-plane=/etc/gap01/keys/cp.key --bind control-plane=control-plane
python gap01_edge_node_supervisor/tools/evidence.py         # machine-readable evidence
python gap01_edge_node_supervisor/tools/exit_gate.py        # formal production exit gate
```

Production service definition: `deploy/systemd/`. Operator procedures: `docs/RUNBOOKS.md`.
Optional `pk_core` conformance gate: see `DEPENDENCIES.md` (runs automatically in `verify.py` when importable).

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run GAP-01`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate GAP-01`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.


## Package layout

| Path | Purpose | Checklist components |
|---|---|---|
| `supervisor.py` | dependency-free lifecycle/drain reference model (unchanged API from 4.2.0) | core |
| `controller.py` | production controller: request pipeline, drain scheduler, reconciliation, partition/emergency/pressure modes, watchdog, probes | 5, 10, 12–15, 20–22, 30, 34–36, 40 |
| `store.py` | checkpoint + WAL, idempotency journal, backup/restore, migrations, hash-chained audit log | 4, 15, 23, 26, 38, 39 |
| `security.py` | authn (HMAC, nonce, skew), authz policy, rate limiting, node attestation, artifact verification | 7, 8, 18, 19, 24 |
| `config.py` | typed/validated/signed config, hot reload, secret boundary | 16, 17, 19, 58 |
| `health.py` | health signal registry and aggregation policy | 9 |
| `runtime.py` | runtime adapter protocol, process adapter, fault-injectable fake, reclaim proof | 3, 11 |
| `inventory.py` | hardware/resource snapshot, pressure sampling | 2, 22 |
| `bootstrap.py` | ordered boot phases, recovery mode, boot attestation, process entry point | 1 |
| `server.py` / `client.py` | 0600 UNIX-socket control endpoint, loopback probes, client helper | 7, 34 |
| `errors.py` / `observability.py` | structured errors; metrics, JSON logs, tracing, SLOs, redaction | 25, 31–33, 36 |
| `schemas/` + `schema_validator.py` | versioned `PK_*` JSON Schemas and validator | 6, 64 |
| `examples/` | protocol sequences and conformance fixtures (recorded from real runs) | 52, 68 |
| `tests/` | unit, property, concurrency, fuzz, integration, SIGKILL chaos | 23–29, 47, 48, 51 |
| `tools/` | coverage, bench, soak, perf gate, evidence, traceability, release build, exit gate, backup | 42, 46, 49, 50, 53, 54, 60 |
| `deploy/` | systemd unit + backup timer, sysusers/tmpfiles, example config, alert rules | 37, 56, 65 |
| `docs/` | ADRs, requirements, threat model, runbooks, capacity, platforms/compat, observability | 55, 57, 58, 69, 70 |
| `CHECKLIST_STATUS.md` | item-level status of all 2,100 missing-components checks | — |
| `TRACEABILITY.*` | 100-requirement traceability matrix | 53 |
| `EXCEPTIONS.md` | named, dated deferrals | — |

## Policies

Security reporting: `SECURITY.md` · Support and EOL: `SUPPORT.md` · Dependencies: `DEPENDENCIES.md` · Open exceptions: `EXCEPTIONS.md` · License: `LICENSE` (not yet selected, EXC-011).

## Dependency behavior

The local supervisor model and the full production controller are usable without `pk_core`:

```python
from gap01_edge_node_supervisor import NodeSupervisor
```

`pk_core` is required only for contract/gate integration. When it is not importable,
`COMPONENT`, `EdgeNodeSupervisorComponent`, and `build_contract` are exported as
`None` rather than making the entire package unimportable.
