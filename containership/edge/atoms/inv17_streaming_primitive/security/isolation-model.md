# INV-17 Tenant / Workload Isolation Model

**Controls:** C046
**Owner:** UNASSIGNED — owner to fill

## Isolation level provided

**Logical isolation inside one process.** INV-17 does not provide memory, CPU or fault isolation;
all tenants share one Python interpreter. Hard isolation (process, sandbox, component instance)
belongs to the host runtime.

## Mechanisms (as implemented)

| Aspect | Mechanism | Code |
|---|---|---|
| Handle ownership | Each `Stream` carries `tenant` and `workload`; `get` refuses mismatches and audits `authz.denied` ("cross-tenant access") | `control::StreamRegistry.get` |
| Token binding | `ten`/`wl`/`aud` claims must match | `security::CapabilityAuthority.verify` |
| Explicit transfer | Only `StreamRegistry.transfer` changes owner; requires single-use `transfer` token; audited `stream.transfer` | `control::StreamRegistry.transfer` |
| Resource isolation | Per-tenant `TenantQuota.max_streams`, `max_buffered`; instance `global_buffer_budget` | `control::TenantQuota`, `StreamRegistry.open`, `write` |
| Fairness | Weighted deficit round-robin for a shared credit pool | `control::FairCreditScheduler.allocate` via `control::StreamRegistry.rebalance` (weights from `TenantQuota.weight`; invoked by the embedding runtime) |
| Blast-radius control | Freeze a tenant or workload scope; freezing affects only matching streams | `StreamRegistry.quarantine`, `release` |
| Lock scope | One lock per stream; registry lock held for admission/quota | `stream::Stream._lock`, `StreamRegistry._lock` |
| Telemetry | Tenant/workload pseudonymised; no tenant label on metrics | `observability::redact`, `MetricsExporter.samples` |

## Non-isolation (explicit)

- A `Stream` object obtained from `open`/`get` can be passed to anyone and used without further checks.
- A slow or hostile element `__class__` can hold one stream's lock; the registry lock is not held during `Stream.write` in `StreamRegistry.write`, but it is held for the quota scan.
- `global_buffer_budget` is shared: one tenant can consume up to its `max_buffered`, and the sum of tenant quotas may exceed the global budget, in which case `LoadShed` affects all tenants.
- `transfer` requires no consent from the destination tenant.

## Verification

Planned: `tests/test_security.py` (cross-tenant get/transfer), `tests/test_control.py` (quotas,
scoped freeze), `tests/test_property.py` (fair allocation invariants), `tests/test_soak.py`.
