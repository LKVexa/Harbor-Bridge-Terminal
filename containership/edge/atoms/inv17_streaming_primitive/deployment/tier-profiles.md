# INV-17 Deployment Tier Profiles

**Controls:** C012, C018
**Owner:** UNASSIGNED — owner to fill
**Machine-readable companion:** `deployment/applicability-matrix.json` (maintained separately)

## Mechanism

`configuration::load_layers(*overlays)` loads `config/defaults.json`, deep-merges overlays in order
(`configuration::merge`: objects recurse, scalars/lists replace), validates the merged document
against `config/stream-config.schema.json`, and enforces CFG-X1 (`max_buffer <= 64 * max_credit`).
The schema enumerates `tier` in `cloud | datacenter | near-edge | far-edge`.
`configuration::to_stream_config` converts the `stream` section into `stream::StreamConfig`.

**Wiring gap:** only the `stream` section is converted by code. The `tenants`, `health` and
`overload` sections are validated but not automatically applied to `control::StreamRegistry`
(the integrator passes `TenantQuota`, `HealthPolicy`, `global_buffer_budget`); `breaker_threshold`
and `breaker_cooldown_s` are not passed anywhere — `StreamRegistry` constructs
`CircuitBreaker(clock=clock)` with defaults 5 / 5 s.

## Profiles

| Setting | defaults.json | cloud (`config/overlays/cloud.json`) | datacenter | near-edge | far-edge (`config/overlays/far-edge.json`) |
|---|---|---|---|---|---|
| environment | dev | production | — | — | production |
| max_credit | 1024 | 4096 | inherits default | inherits default | 64 |
| max_buffer | 1024 | 4096 | inherits default | inherits default | 64 |
| idempotency_window | 1024 | inherits | inherits | inherits | inherits (1024) |
| tenant default quota | 64 streams / 65 536 buffered / weight 1 | inherits | inherits | inherits | inherits |
| global_buffer_budget | 1 048 576 | inherits | inherits | inherits | 16 384 |
| breaker threshold / cooldown | 5 / 5 s (config only) | inherits | inherits | inherits | 5 / 5 s |

Overlay files for **datacenter** and **near-edge** do not exist in `config/overlays/` at v4.3.0.
Selecting those tiers today means setting `"tier"` in a site overlay and inheriting defaults.
PROPOSED (not implemented) direction: datacenter follows cloud; near-edge sits between (e.g. a
reduced global budget). Any values must be derived from `tools/capacity.py` output, not guessed.

Note for far-edge: the idempotency window (1024 keys) exceeds max_credit (64); memory for the
window is bounded by key count, not by the credit ceiling.

## Applicability by tier

| Concern | cloud | datacenter | near-edge | far-edge |
|---|---|---|---|---|
| Stream semantics (credit, EOS, drop, typing) | Applies | Applies | Applies | Applies |
| Capability tokens / trust deps | Applies | Applies | Applies | Applies; time-source outage more likely -> fail closed (see `security/trust-dependency-failure.md`) |
| Failover / distributed | N/A (instance-local) | N/A | N/A | N/A — see `resilience/distributed-applicability.md` |
| Status HTTP endpoint | Optional | Optional | Optional | Optional; loopback only |
| Power/thermal | Not measured | Not measured | Not measured | Not measured; waiver pending (`benchmarks/power-thermal.md`) |

## Usage

```python
from inv17_streaming_primitive.configuration import load_layers, to_stream_config
doc = load_layers("config/overlays/far-edge.json", {"site": "edge-17"})
cfg = to_stream_config(doc)
```

Validation failures raise `configuration::ConfigInvalid` (fail closed). Tests: planned under
`tests/test_control.py` / `tests/test_property.py`.
