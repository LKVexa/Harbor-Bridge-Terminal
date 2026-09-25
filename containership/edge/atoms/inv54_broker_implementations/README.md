# INV-54 - Broker implementations

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Audit source:** `CHECKLIST.json`; the master-prompt corpus is not included in this component archive.

Broker implementations are the concrete engines behind the messaging contract. Two ship here: a fan-out broker that copies each message to every subscriber, and a partitioned log that keeps per-key order and lets consumers replay from an offset. They make opposite trade-offs, and the contract is only portable if both pass the same checks.

## v4.3.0 production layer (missing-component overhaul)

v4.3.0 executes `docs/checklist/INV54_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (100 components)
against this package. The reference brokers are unchanged; a stdlib-only production layer, three
provider adapters, schemas, configuration, operations documents and an evidence generator were added.

| Area | Where |
|---|---|
| multi-tenant service (authn, authz, quotas, admission, audit, health) | `service.py`, `security.py`, `quota.py`, `resilience.py` |
| errors / lifecycle / versions | `errors.py`, `lifecycle.py`, `negotiation.py`, `schemas/` |
| configuration (fail-closed, overlays, provenance, rollback, secrets) | `config.py`, `config/` |
| durable storage, retention, encryption, backup | `storage.py` |
| replication, fencing, residency | `ha.py` |
| telemetry, tracing, decisions, explain | `telemetry.py`, `ops/` |
| Kafka / RabbitMQ / SQS adapters + conformance | `adapters/` |
| benchmarks + regression gate | `bench/` |
| governance, security, runbooks | `docs/`, `CODEOWNERS`, `SECURITY.md`, `LICENSE-PENDING.md` |
| evidence (tests, conformance, status, traceability, SBOM, checksums, exit gate) | `tools/gen_evidence.py` -> `evidence/` |

```
python -B -m unittest discover -s inv54_broker_implementations/tests -p 'test_*.py'
python inv54_broker_implementations/bench/harness.py --gate
python -B inv54_broker_implementations/tools/gen_evidence.py
python -m inv54_broker_implementations validate-config inv54_broker_implementations/config/base.json inv54_broker_implementations/config/overlays/production-kafka.json
```

**Status, stated plainly:** see `CHECKLIST_STATUS.md` and `evidence/exit_gate.json`. The exit gate is
**NO_GO**: no component is PASS because none has an independent review record, and Kafka/RabbitMQ/SQS
certification, `pk_core` certification, edge-hardware, soak and fleet evidence do not exist yet.
Provider adapters are verified only against in-process fake clients and must not be advertised as supported.

## Responsibility

Own the reference brokers: fan-out and partitioned-log implementations, per-key ordering, consumer offsets and replay, and contract conformance of each.

## Owns

- The fan-out broker
- The partitioned-log broker
- Per-key ordering by partition
- Consumer offsets and replay
- Broker conformance against the messaging contract

## Explicitly does not own

- The messaging contract
- Delivery guarantees policy
- Cluster operation
- Schemas
- Transport

## Non-goals

- Defining the contract
- Running a cluster
- Owning schemas

## Interfaces

- `fanout` - PK_BROKER_FANOUT/1 - copy-to-all delivery
- `log` - PK_BROKER_LOG/1 - partitioned, offset-addressed log
- `offset` - PK_BROKER_OFFSET/1 - a consumer's committed position

## Service-level objectives

- **ordering** - zero per-key reorderings in the log broker (error budget: no budget)
- **fan-out completeness** - every subscriber receives every message (error budget: no budget)
- **append latency** - p99 append under 2ms (error budget: 1% may exceed)

## Running it

```
python inv54_broker_implementations/tests/test_brokers.py     # dependency-free broker tests
python inv54_broker_implementations/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-54 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-54 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Reference-implementation hardening

- Broker primitives live in `brokers.py` and can be imported/tested without `pk_core`.
- Fan-out delivery deep-copies each message per subscriber and prepares all copies before mutation, preventing cross-subscriber aliasing and partial delivery on copy failure.
- Broker state cannot be injected through dataclass constructors, and partition count is immutable after construction.
- Partition, offset, limit, consumer, subscriber, and key inputs are validated explicitly; booleans are not accepted as integer indices.
- Shared in-memory state is protected with re-entrant locks so append/poll/seek and subscribe/publish operations are atomic within one process.
- The reference brokers remain in-memory; the v4.3.0 production layer above wraps them. Per-component status is in `CHECKLIST_STATUS.md`.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-54`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-54`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
