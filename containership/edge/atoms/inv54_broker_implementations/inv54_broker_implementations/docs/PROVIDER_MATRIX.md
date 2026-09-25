# Provider capability matrix  (component 16) — normative source: `schemas/provider_matrix.json`

| Feature | reference | kafka | rabbitmq | sqs |
|---|---|---|---|---|
| per-key order | native | native | unsupported | emulated (FIFO MessageGroupId only) |
| replay from offset | native | native | unsupported | unsupported |
| independent consumer offsets | native | native | unsupported | unsupported |
| fan-out to all subscribers | native | emulated (one group per subscriber) | native | emulated (client-side, non-atomic; use SNS) |
| ack + redelivery | emulated | emulated (commit-on-ack) | native | native (visibility timeout) |
| dedup window | emulated (idempotency cache) | unsupported (idempotent producer covers producer retries only) | unsupported | native (FIFO, 5 min) |

Unsupported features raise `INV54-E0904`. Certification status per provider: **UNVERIFIED** (fake-client conformance only).
