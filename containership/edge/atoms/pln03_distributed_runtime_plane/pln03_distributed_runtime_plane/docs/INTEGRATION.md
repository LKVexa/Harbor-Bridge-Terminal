# Adjacent-plane integration contracts (MC-019, MC-028, MC-029, MC-031, MC-053)

| Plane | Direction | Contract PLN-03 relies on | Tested here | Remaining |
|---|---|---|---|---|
| PLN-02 Application | upstream | Supplies bindings `<workload>:<capability>` → adapter; immutable per revision | binding validation (`DistributedRuntime.__init__`) with in-process doubles | end-to-end test against real PLN-02 |
| INV-49 Adapters | upstream | Implements `Adapter` surface (get/set/delete/transact/accept/publish/messages/invoke); raises `AdapterUnavailable` | reference + `DurableAdapter` | real adapter conformance run |
| PLN-04 Execution | downstream | Hosts runtime; provides process/Wasm/microVM isolation for adapters (MC-028) and execution/memory/network/device isolation (MC-031) | — | **not integrated** |
| PLN-06 Data | downstream | Takes payloads > 1 MiB | limit enforced (`PK_PAYLOAD_TOO_LARGE`) | handoff test |
| PLN-07 Security | peer | Issues capability tokens (`pk.captoken/1`), keys, revocation, trusted time; node/peer identity + transport encryption (MC-029, MC-032) | verifier + outage policy | **mTLS/SPIFFE identity, KMS, at-rest encryption not integrated** |

Integration tests against these planes cannot be written inside this single-component archive because none of those planes is packaged here or pinned in `DEPENDENCIES.lock.json`.
