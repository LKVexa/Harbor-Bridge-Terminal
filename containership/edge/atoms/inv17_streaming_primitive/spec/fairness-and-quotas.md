# INV-17 Fairness and Quotas

**Controls:** C017, C028 (checklist §11). Source: `control::TenantQuota`, `control::FairCreditScheduler`, `control::StreamRegistry`.

## 1. Quotas (`TenantQuota`)

| Field | Default | Enforced in | Error |
|-------|---------|-------------|-------|
| `max_streams` | 64 | `StreamRegistry.open` (count of open streams with that tenant) | `QuotaExceeded` + audit `quota.denied` |
| `max_buffered` | 65536 | `StreamRegistry.write` (`buffered_total(tenant)`) | `QuotaExceeded` (counted in `shed_count`) |
| `weight` | 1 | `FairCreditScheduler` weights | – |

All fields must be positive `int`. Per-tenant quotas come from `StreamRegistry(quotas=...)`; others use `default_quota`. Config source: `tenants` in `config/defaults.json`.

Instance-wide: `global_buffer_budget` (default 1,048,576; far-edge overlay 16,384) → `LoadShed`.

Per-stream: `StreamConfig.max_credit` / `max_buffer` (default 1024; cloud overlay 4096; far-edge 64).

Quotas are **per tenant**, not per workload; workload is used for authorization binding and quarantine scope only.

## 2. Fair credit allocation (`FairCreditScheduler.allocate(pool, demand)`)

Weighted deficit round-robin:

- Tenants with demand > 0 are visited in sorted order each round.
- Each visit adds `max(1, weight)` to that tenant's deficit and grants `min(deficit, remaining demand, pool)`.
- A tenant leaves when satisfied (deficit reset to 0). Loop ends when the pool or demand is exhausted.
- Deficits carry across calls for unsatisfied tenants.

Properties: total granted ≤ pool; no tenant exceeds its demand; any tenant with demand receives ≥ 1 unit per round while the pool lasts (no starvation); weights skew share, not access. A `pool < 0` raises `ValueError`.

`StreamRegistry.rebalance(pool)` wires the scheduler into the registry: eligible streams are those in state `open` or `credit_stalled` (frozen/terminated get nothing); per-tenant demand is Σ(`max_credit − credit`); weights are set from `TenantQuota.weight`; each tenant's share is then granted one unit at a time round-robin over its streams. It returns the per-tenant grants. The registry does not call `rebalance` on its own; the embedding runtime decides when to call it.

## 3. Isolation

Cross-tenant access through `StreamRegistry.get` is refused (`AuthzDenied`, audit `authz.denied`). Ownership changes only through `StreamRegistry.transfer`, which requires a single-use `transfer` right.
