# ADR-0001 — Broker-independent messaging contract over Dapr Pub/Sub

* Status: **PROPOSED** — not approved. Approval requires the accountable owner and the architecture reviewer named in `governance/owners.json` (both UNASSIGNED) and a record in `governance/approvals.json`.
* Deciders: UNASSIGNED · Date drafted: 2026-09-22 · Supersedes: none

## Context

INV-52 must let applications publish and subscribe without knowing the broker (source function: *message routing and delivery*). The Post-Kubernetes series places the application runtime at INV-46 (Dapr) and broker implementations at INV-54.

## Decision

1. The contract is the envelope `PK_MSG_ENVELOPE/1` (`id, source, type, time, data`, optional `traceparent`), topic-scoped publishing and predicate routing with a dead-letter path.
2. On the wire the envelope maps 1:1 onto **CloudEvents 1.0 structured mode**, which is what Dapr Pub/Sub publishes and delivers (`adapters.to_cloudevent`/`from_cloudevent`). Numeric `time` travels as extension `pkmsgtime`.
3. The production transport is the **Dapr Pub/Sub building block** via the sidecar HTTP API `POST /v1.0/publish/{pubsubname}/{topic}`; inbound delivery maps to Dapr's `SUCCESS / RETRY / DROP`, and `DROP` feeds the Dapr `deadLetterTopic`.
4. INV-52 owns routing semantics and the dead-letter decision; durability/redelivery stay in INV-53 and the broker.
5. Identity is established before INV-52 (INV-46 / `TenantBus` tokens); INV-52 never trusts `source` without it.

## Alternatives considered

| Option | Why not chosen |
|---|---|
| Direct broker SDKs (Kafka, NATS, Service Bus) behind an in-house interface | re-implements what Dapr components already provide; N adapters to certify |
| CloudEvents SDK + custom HTTP bus | no subscription/dead-letter management, no scoping |
| Durable in-process queue | violates "broker-independent" and moves durability into INV-52 |

## Consequences

* Positive: one contract for all tiers; broker swap is a Dapr component change; conformance fixtures apply to any adapter.
* Negative: a live `daprd` is a runtime dependency for production; Dapr version support windows force regular upgrades (COMPATIBILITY.md).
* Risk: the in-process reference runtime can be mistaken for a durable broker — listed as an unsupported pattern (SCOPE.md).

## Evidence required before approval

Live Dapr integration run against the pinned version (OPEN), broker matrix run (OPEN), threat model review (OPEN).
