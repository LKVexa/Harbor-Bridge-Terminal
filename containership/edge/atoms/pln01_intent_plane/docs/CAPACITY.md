# Capacity model, quotas and fairness (MC-007)

| Limit | Default | Config key | Enforcement |
|---|---|---|---|
| nodes per graph | 10 000 | limits.max_nodes | E0005 |
| nodes per tenant | 5 000 | quotas.tenant_max_nodes | E0011 |
| request rate per tenant | 50/s, burst 100 | quotas.tenant_rate_per_second / tenant_burst | token bucket, E0011 |
| concurrent requests | 64 | quotas.max_concurrent_requests | bulkhead |
| queued requests | 256 | quotas.max_queue_depth | shed with E0012 |
| deps per node | 256 | limits.max_dependencies_per_node | E0001 |
| spec size | 1 MiB | limits.max_spec_bytes | E0001 |
| history / replay / audit windows | 64 / 4096 / 8192 | limits.* | bounded deques |
| transaction size | 1 000 requests | fixed | E0001 |

**Fairness:** each tenant has an independent bucket, so one tenant's flood cannot consume another's rate
(`test_tenant_rate_quota_is_isolated`). Per-tenant overrides: `TenantQuotas.overrides[tenant]`.

**Saturation formulas:** `bulkhead_saturation = (in_flight + waiting) / (max_concurrent + max_queue)`;
memory ≈ `909 B × nodes` (+ history deltas) from `benchmarks`; plan CPU ≈ O(V + E log V).

**Scaling signals:** scale up (vertical) or shard by tenant when `pln01_bulkhead_saturation > 0.7` for 10 min,
`E0011` rate > 1 % of requests, or `intent_graph_nodes > 0.8 × max_nodes`.
