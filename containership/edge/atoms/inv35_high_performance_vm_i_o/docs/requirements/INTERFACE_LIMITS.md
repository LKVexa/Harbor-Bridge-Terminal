# Published interface and resource limits (C028, C067)

| Limit | Value | Where enforced | Code on breach |
|---|---|---|---|
| Descriptors per chain | ≤ `max_chain` (default 16, ceiling `MAX_CHAIN`=16) | `VirtQueue.chain_limit` | E103 |
| Bytes per chain | ≤ `max_chain_bytes` (default 1 MiB, ceiling 1 GiB) | `VirtQueue.byte_limit` | E107 |
| In-flight descriptors per queue | ≤ `queue_depth` (default 64, ceiling 64) | `VirtQueue.depth_limit` | E200 |
| Queues per tenant | ≤ `max_queues_per_tenant` (16) | `ControlPlane.register_queue` | E201 |
| Tenant share of host capacity | `tenant_share` × `host_descriptor_capacity` | `QuotaManager` | E201 |
| Tenant submit rate | `submit_rate_per_s`, burst `submit_burst` | `TokenBucket` | E201 |
| Descriptors in a wire request | ≤ 64 | request schema `maxItems` | E106/E100 |
| Capability TTL | ≤ 3 600 s, clock skew 5 s | `Authority` | E302 |
| Replay window | 65 536 nonces (LRU) | `Authority._seen` | E304 |
| Verified-token cache | 1 024 tokens (LRU) | `Authority._verified` | — |
| Idempotency cache | 4 096 keys (LRU) per host | `IdempotencyCache` | — (older keys forgotten; documented) |
| Completion history | ≤ `QUEUE_DEPTH` records | `VirtQueue.completed` | — |
| Decision history | 4 096 | `Runtime.decisions` | — |
| Log buffer | 4 096 records | `StructuredLog` | — |
| Metric series per metric | 256, then `__overflow__` | `Metrics` | — |
| Config history | 8 snapshots | `ConfigStore` | — |
| Retry attempts / budget | ≤ 10 attempts, default 4 / 500 ms | `RetryPolicy` | — |

**Resource-bound model.** Host memory is O(queues × depth + tenants + cache sizes);
every structure above is bounded, so no guest or tenant input grows memory
without limit. Fan-out: one submit touches exactly one queue and one tenant
bucket. Concurrency: all mutation is serialised under `Runtime._lock` (the
reference model's choice; production backends shard per queue).
