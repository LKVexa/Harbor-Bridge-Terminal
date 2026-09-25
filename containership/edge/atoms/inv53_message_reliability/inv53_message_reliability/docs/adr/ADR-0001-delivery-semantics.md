# ADR-0001 — At-least-once delivery with fenced visibility leases and bounded attempts

- **Status:** PROPOSED (not approved — `governance/owners.json` names no approver)
- **Date proposed:** 2026-09-22 · **Version:** applies from 5.0.0, extended in 5.1.0
- **Deciders required:** technical_owner, security_owner

## Context
INV-53 must turn "published" into "processed" across unreliable edge networks (MASTER.md audit context).
Consumers crash, links partition, and brokers restart. The component owns acknowledgement, visibility,
redelivery, attempt caps, dead-lettering and consumer idempotency; it does not own ordering or routing.

## Decision
1. **At-least-once**, never at-most-once: a message is owned by the broker until an ack by its *current*
   lease; consumers deduplicate by `(scope, message id)`.
2. **Visibility leases with opaque fencing tokens.** Each delivery gets a fresh 128-bit token; ack/nack/extend
   must present the current token and an explicit time. Stale and late tokens are refused (5.0.0).
3. **Bounded attempts** (`max_attempts`), then **dead-letter** with reason, attempts and last token.
4. **Durability by write-ahead journal** (5.1.0): transition written + fsynced before it is applied; recovery
   replays; a torn final record is truncated, anything else refuses to open.
5. **Single writer per store**: OS lock + monotonically increasing epoch file; a superseded writer is fenced.

## Alternatives rejected
| Alternative | Why rejected |
|---|---|
| Exactly-once delivery | Not achievable end-to-end without transactional coupling to the consumer's effect store; claims of it hide duplicates. At-least-once + dedupe is honest. |
| At-most-once (ack on receive) | Loses messages when a consumer crashes — violates the component's core responsibility. |
| Ack by message id only (≤ 4.1.0) | A stale consumer could settle a newer delivery; fixed in 5.0.0. |
| Infinite retry | Poison messages loop forever and starve healthy traffic. |
| Wall-clock inside the queue | Makes deadline behaviour untestable and couples to clock skew; the queue takes an explicit logical `now`. |
| Embedded SQLite for durability | Would work, but the append-only journal gives a replayable, hash-chained audit of every transition with no extra dependency; SQLite remains a candidate for an INV-54 adapter. |
| Raft/consensus inside INV-53 | Belongs to the broker/replication layer (INV-54, GAP-05); INV-53 defines the fencing contract they must honour. |

## Consequences
Consumers must be idempotent. Throughput per queue is bounded by one serialized journal (measured in
`docs/perf/PERFORMANCE.md`). Cross-host ownership needs an external consensus service (DEBT-01).

## Review trigger
Any change to the ack contract, the journal format (`inv53.store/*`), or the wire major version.
