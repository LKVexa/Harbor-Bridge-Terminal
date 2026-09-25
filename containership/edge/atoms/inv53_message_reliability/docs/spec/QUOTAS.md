# Quota, capacity and fairness (C017, C028)

| Limit | Key | Default | Enforcement point | Outcome |
|---|---|---|---|---|
| Ready depth per queue | `max_ready` | 100,000 | before put / requeue / redrive | `E_CAPACITY` |
| In-flight per queue | `max_in_flight` | 10,000 | before lease | `E_CAPACITY` |
| Dead letters per queue | `max_dead_letters` | 100,000 | before dead-letter; a lease that cannot be dead-lettered stays in flight | `E_CAPACITY` |
| Message size | `max_message_bytes` | 256 KiB (canonical JSON) | put | `E_CAPACITY` |
| Lease extension | `max_lease_extension_seconds` | 300 | extend | `E_CAPACITY` |
| Queues per tenant | `max_queues_per_tenant` | 64 | first put to a new queue | `E_CAPACITY` |
| Request rate per tenant | `tenant_rate_per_second` / `tenant_burst` | 500 / 1,000 | token bucket before the op | `E_QUOTA` |
| Load shedding | `shed_ready_ratio` | 0.9 × max_ready | puts only; consumers keep draining | `E_SHED` |
| Wire field lengths | id 512, tenant/queue 128, lease 128, reason 256 | validator | `E_VALIDATION` |
| Metrics series | `Metrics.max_series` | 2,000 | exporter; drops counted in `inv53_metrics_dropped_series` | — |
| Replay nonces | `nonce_cache` | 100,000 | authenticator; saturation inside the skew window fails closed | `E_SECURITY_DEPENDENCY` |

Fairness: each tenant has its own token bucket, so one tenant cannot consume another's rate. Within a
queue delivery is FIFO by ready order (not a guarantee — ordering is not owned).
