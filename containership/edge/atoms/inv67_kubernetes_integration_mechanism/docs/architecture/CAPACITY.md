# Capacity, quota and fairness model (items 06, 40)

Enforcement point: `plane/resilience.py::Admission` inside the controller, before any downstream call.

* **Global ceiling** `maxInflight` (default 256) concurrent placement calls.
* **Per-tenant ceiling** `tenantInflight[tenant]`, default `defaultTenantInflight` (16). Unknown tenants get the default, never unlimited.
* **Per-tenant rate** token bucket `tenantRatePerSec` / `tenantBurst`.
* **Fan-out bound:** ≤ 32 containers per workload (CRD `maxItems`).
* **Overload behavior:** shed with retryable `INV67_OVERLOADED`/`INV67_QUOTA_EXCEEDED`; the key is requeued with jitter — no busy loop, no silent drop.
* **API-server rate assumption:** ≈3 writes per new workload (finalizer, status×1–2); steady-state observe writes only on state change.

## Planning model

`plane/capacity.py::Model`: throughput ≈ workers / (api_rtt × writes + downstream_rtt + cpu). With defaults (10 ms API, 20 ms downstream) one worker ≈ 24 reconciles/s. Saturation = offered > 80 % of model. Local measurement (`evidence/perf/latest.json`) over in-memory fakes is ~1.6 k workloads/s, i.e. the controller CPU is not the bottleneck; real RTTs are. **Fleet-scale certification against a real cluster has not been run (EXC-007).**

## Regression gate

`capacity.regression()` fails a release when any `*_p99_ms` grows or `*_per_s` drops beyond tolerance vs `evidence/perf_baseline.json`.
