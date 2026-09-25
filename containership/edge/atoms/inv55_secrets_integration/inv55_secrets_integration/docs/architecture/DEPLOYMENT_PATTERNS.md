# Deployment patterns (INV55-DEP-001, DRAFT)

| Pattern | Topology | Provider access | Cache / stale policy | Status |
|---|---|---|---|---|
| Cloud region | 1 INV-55 instance per workload node (sidecar) → regional Vault cluster | TLS/mTLS, AppRole | fresh 30 s, stale **off** | supported (design) |
| Datacenter | same as cloud; Vault on-prem cluster | mTLS required | fresh 30 s, stale off | supported (design) |
| Near edge | instance per site → regional Vault over WAN; read replica at site via `FailoverProvider` | mTLS required | fresh 30 s; stale ≤ 5 min only with waiver | conditional (W-004) |
| Far edge / disconnected | instance per device; intermittent uplink | mTLS | stale serving needs a waiver; offline-deny default | **unsupported** until W-004 closes |
| Single global instance | — | — | — | **unsupported** (contract: "nothing assumes a global singleton") |

Residency: a secret's tenant namespace maps to one Vault namespace in one jurisdiction; cross-region replication of a tenant namespace requires the tenant's residency approval. Locality: sidecar model keeps plaintext on-node; no plaintext crosses the INV-55 wire boundary (R-REF-02).
