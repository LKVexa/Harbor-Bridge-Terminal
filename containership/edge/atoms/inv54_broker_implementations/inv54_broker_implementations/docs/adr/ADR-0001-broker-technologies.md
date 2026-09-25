# ADR-0001 — Broker technologies: Kafka, RabbitMQ, AWS SQS  (controls C010, C031)

- **Status:** PROPOSED (unapproved — accountable-owner approval record required for PASS)
- **Date:** 2026-09-22 · **Deciders:** accountable owner (pending) · **Supersedes:** none

## Context
The contract requires a fan-out broker and a partitioned, replayable log with per-key order and
independent consumer offsets. v4.2.0 shipped only in-memory reference implementations.

## Decision
1. **Kafka** is the preferred provider for `PK_BROKER_LOG/1` (native partitions, per-key order,
   committed offsets, replay). Client: `confluent-kafka==2.6.1`, idempotent producer, `acks=all`,
   manual commits.
2. **RabbitMQ** is supported for `PK_BROKER_FANOUT/1` only (fanout exchange + one durable queue per
   subscriber group, publisher confirms, persistent messages). Replay/offsets are **excluded**:
   the adapter refuses them with `INV54-E0904`. Client: `pika==1.3.2`.
3. **AWS SQS** is supported for work-queue delivery with ack/redelivery and FIFO dedup. Per-key
   order only on FIFO queues; replay/offsets **excluded**. Fan-out via SNS→SQS is recommended;
   the adapter's client-side fan-out is non-atomic and documented as such. Client: `boto3==1.35.99`.
4. The **durable** built-in provider (`storage.DurableLog` + `ha.ReplicatedPartition`) is the edge /
   offline profile where no managed broker exists.
5. The **reference** in-memory provider is dev/test only; `config.validate` rejects it under
   `profile=production`.

## Alternatives considered
- NATS JetStream / Pulsar: capable of both semantics; rejected for now — no owner demand, adds a
  fourth certification surface. Revisit on request.
- Emulating replay on RabbitMQ/SQS by mirroring into a side log: rejected — it silently changes
  durability/ordering guarantees owned by INV-53.

## Consequences
- Feature matrix in `schemas/provider_matrix.json` is normative; tests assert adapters declare
  exactly the `native` features.
- Provider certification against real clusters is outstanding (`tools/certify_providers.py`); until
  then every provider is **UNVERIFIED** and must not be advertised as supported (roll-up item 4).
- Rollback: disabling a provider is a config change (`provider.kind`), validated fail-closed.
