# Capacity, quotas, fairness, capacity model and saturation (MC-009, MC-057, MC-059)

## Quotas and ceilings (defaults; per-site overlays may tighten)
| Resource | Default | Enforced by | On exceed |
|---|---|---|---|
| nodes per tenant graph | 10 000 | `TopologyLimits.max_nodes` | `TOPO.QUOTA_EXCEEDED` (whole batch rejected) |
| links per tenant graph | 50 000 | `max_links` | same |
| links per node (fan-out) | 1 024 | `max_degree` | same |
| capabilities per node | 64 | `max_caps_per_node` | same |
| tenants per instance | 1 024 | `max_tenants` | `QUOTA_EXCEEDED` / `OVERLOADED` |
| request rate per tenant | 500/s, burst 1 000 | `Admission` | `RATE_LIMITED` + retry_after |
| concurrent requests | 256 | `Admission.max_in_flight` | `OVERLOADED` |
| replay cache | 100 000 nonces | `ReplayCache` | fail closed (`OVERLOADED`) |
| idempotency entries | 50 000 / 600 s | `IdempotencyStore` | oldest evicted (documented weakening) |
| decision records | 10 000 | `DecisionLog` | oldest evicted |

**Fairness:** buckets are per tenant and are charged only *after* authentication and authorisation, so one
tenant (or an anonymous flood) cannot consume another tenant's budget. Mutations and queries share one bucket
(cost 1 each) in v1.

## Capacity model
Resolve cost ≈ O((V' + E') log V') where V'/E' are the nodes/links closer than the answer (early-terminating
walk); partition checks are cached per graph revision (one full walk per revision). Apply cost ≈ O(V + E) per
batch (copy-on-write clone) + O(k) per mutation, so feeds should batch (≤ 1 000 mutations). Memory ≈ 1.2 KiB
per node+link pair at the defaults (see `perf/baseline.json` `bytes_per_tenant` for a 6-node graph ≈ 12 KiB).
Sizing: `instances_per_site = 1`; a site instance serving `Q` resolves/s needs `Q × p50_wire` CPU-seconds/s
(≈ 0.8 ms on the reference host).

## Saturation signals and scale triggers
| Signal | Metric | Trigger |
|---|---|---|
| admission shedding | `inv62_errors_total{code="TOPO.RATE_LIMITED"}`, `…OVERLOADED` | > 1 % of requests for 10 min → raise limits or split tenants |
| in-flight | `health().in_flight` | > 80 % of `max_in_flight` |
| graph size | `inv62_nodes{tier}` | > 80 % of `max_nodes` |
| latency | `inv62_request_latency_ms` p99 | > 2.5 ms (wire) |
| state store | `health().circuit` | not `closed` |
