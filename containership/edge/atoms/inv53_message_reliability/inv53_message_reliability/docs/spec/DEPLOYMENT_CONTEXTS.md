# Deployment-context requirement matrix (C012)

| Concern | Cloud | Datacenter | Near-edge | Far-edge (intermittent) |
|---|---|---|---|---|
| Store | DurableQueue on replicated block storage; INV-54 broker adapter preferred | DurableQueue on local SSD, backup nightly | DurableQueue on local SSD | DurableQueue on local flash; `fsync=true` mandatory |
| `visibility_seconds` | 30 | 30 | 60 | 300 (slow links, long processing) |
| `max_attempts` | 5 | 5 | 8 | 10 (transient link loss is not poison) |
| `max_ready` | 1,000,000 | 100,000 | 50,000 | 10,000 (bounded flash) |
| Authentication | required, keys via KMS provider | required, KMS | required, EnvKeyProvider or KMS | required, EnvKeyProvider (KMS unreachable while disconnected) |
| Audit sink | local file + shipped | local file + shipped | local file, shipped on reconnect | local file, head anchored on reconnect |
| Ownership | one writer per store; cross-host consensus via broker | same | same | single node by construction |
| Clock | NTP-disciplined | NTP | NTP, skew ≤ 5 s | may drift; `skew_seconds` widened to 900; leases use the broker's own clock |
| Telemetry export | Prometheus scrape | scrape | scrape, sampled logs | buffered; `inv53_*` gauges read on reconnect |

Overrides are expressed as config layers: `base` → `env:<cloud|dc|near-edge|far-edge>` → `site:<id>`
(`config.layer`), each recorded in the provenance map of the effective config. Unknown keys are refused.
