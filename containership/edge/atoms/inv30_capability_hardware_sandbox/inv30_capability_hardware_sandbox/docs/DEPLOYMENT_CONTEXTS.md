# Deployment-context requirements (INV30-GAP-010 · INV-30-C012, C018)

| Context | Overlay | Hardware expectation | Limits | Connectivity behaviour |
|---|---|---|---|---|
| cloud | `config/overlays/cloud.json` | CHERI instances rare → model tier for non-hardware workloads; hardware workloads refused | defaults | Control plane reachable; auth nonce cache local |
| datacenter | `datacenter.json` | Morello/CHERI-RISC-V boards possible in dedicated racks | defaults | as cloud |
| near-edge | `near-edge.json` | Occasional Morello dev boards | inflight 64, caps 131 072 | Intermittent: service keeps serving existing handles; mint needs local minting key only (no remote dependency) |
| far-edge | `far-edge.json` | Usually none | inflight 16, caps 16 384, 4 096/tenant, 64 tenants | Offline-capable: all checks local; telemetry buffered (bounded) and dropped oldest-first; audit ledger local + anchored head exported on reconnect |

**Rules:** the same immutable artifact runs everywhere; only the overlay changes (C035). Discovery (GAP-02) decides
availability per node — never the context label. When connectivity is absent INV-30 SHALL NOT widen any
authority or relax any check; it only loses telemetry export and remote attestation refresh, and new peers whose
attestation cannot be verified are refused (C048).
