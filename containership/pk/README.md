# Post-Kubernetes master-applied components -- UC270

Batches 1 through 6 of the Post-Kubernetes Master Prompt & Workflow Series
v4.0.0, applied to **Unikernel_Containership_v2.7.0_MasterApplied/UC270**.

## Why these elements are owned here

UC270 is the unikernel/microVM containership: it owns the hull, the berths and the conformance gates that decide what may execute. The elements deciding isolation boundaries and the authority crossing them belong beside UC_GATE_RESULTS, and with batch 3 the whole execution substrate they stand on -- the virtualization primitive, the microVM and unikernel tiers, capability security and the hardening mechanisms -- lands here too.

## Owned by this project (22)

| Element | Name | Package |
|---|---|---|
| `INV-23` | Hardware virtualization primitive | `pk_components/inv23_hardware_virtualization_primitive/` |
| `INV-24` | MicroVM runtime | `pk_components/inv24_microvm_runtime/` |
| `INV-25` | MicroVM devices | `pk_components/inv25_microvm_devices/` |
| `INV-26` | MicroVM snapshotting | `pk_components/inv26_microvm_snapshotting/` |
| `INV-27` | Unikernel execution | `pk_components/inv27_unikernel_execution/` |
| `INV-28` | Unikernel implementations | `pk_components/inv28_unikernel_implementations/` |
| `INV-29` | Hybrid Wasm/unikernel | `pk_components/inv29_hybrid_wasm_unikernel/` |
| `INV-30` | Capability hardware sandbox | `pk_components/inv30_capability_hardware_sandbox/` |
| `INV-31` | Function execution architecture | `pk_components/inv31_function_execution_architecture/` |
| `INV-32` | Elastic virtualization | `pk_components/inv32_elastic_virtualization/` |
| `INV-33` | Virtualization controller | `pk_components/inv33_virtualization_controller/` |
| `INV-34` | Legacy CPU expansion path | `pk_components/inv34_legacy_cpu_expansion_path/` |
| `INV-35` | High-performance VM I/O | `pk_components/inv35_high_performance_vm_i_o/` |
| `INV-39` | Process sandbox tier | `pk_components/inv39_process_sandbox_tier/` |
| `INV-40` | Full virtualization tier | `pk_components/inv40_full_virtualization_tier/` |
| `INV-41` | Capability security | `pk_components/inv41_capability_security/` |
| `INV-42` | Capability descriptors | `pk_components/inv42_capability_descriptors/` |
| `INV-43` | Transient-execution defense | `pk_components/inv43_transient_execution_defense/` |
| `INV-44` | Wasm hardening system | `pk_components/inv44_wasm_hardening_system/` |
| `INV-45` | SFI mechanisms | `pk_components/inv45_sfi_mechanisms/` |
| `PLN-04` | Execution plane | `pk_components/pln04_execution_plane/` |
| `PLN-07` | Security plane | `pk_components/pln07_security_plane/` |

## Installed as integration dependencies (73)

These elements are owned by another project in the estate but are installed here
because an owned element's requirement is discharged by calling them -- PLN-07
cannot bind a grant to a signature without GAP-07, PLN-04 cannot root attestation
without GAP-06. They ship as code and checklist; their master prompts live with
their owner.

- `GAP-01` Edge Node Supervisor
- `GAP-02` Hardware capability discovery
- `GAP-03` Topology-aware scheduler
- `GAP-04` Disconnected-operation controller
- `GAP-05` State replication/consistency model
- `GAP-06` Device identity and attestation
- `GAP-07` Artifact provenance/signing
- `GAP-08` OTA lifecycle/rollback
- `GAP-09` Unified observability
- `GAP-10` Power/thermal-aware scheduling
- `GAP-11` Accelerator scheduling
- `GAP-12` WAN resilience and NAT traversal
- `GAP-13` Policy engine
- `GAP-14` Data-gravity manager
- `GAP-15` Runtime compatibility certification
- `INV-01` Legacy infrastructure substrate
- `INV-02` Container substrate
- `INV-03` Container hardening
- `INV-04` Current orchestration
- `INV-05` Current control-state system
- `INV-06` Traditional IaC
- `INV-07` GitOps transition layer
- `INV-08` Dynamic infrastructure model
- `INV-09` Portable compute ISA
- `INV-10` Component composition system
- `INV-11` Interface contract language
- `INV-12` Language interoperability
- `INV-13` System interface
- `INV-14` Previous asynchronous model
- `INV-15` New asynchronous ABI
- `INV-16` Async component functions
- `INV-17` Streaming primitive
- `INV-18` Completion primitive
- `INV-19` OS asynchronous analogues
- `INV-20` HTTP component worlds
- `INV-21` Local service chaining
- `INV-22` Alternative WASI branch
- `INV-36` Control transport
- `INV-37` Bulk data plane
- `INV-38` Kernel-bypass transport
- `INV-46` Distributed application runtime
- `INV-47` Dapr deployment model
- `INV-48` Service communication APIs
- `INV-49` Pluggable infrastructure adapters
- `INV-50` State abstraction
- `INV-51` Example state stores
- `INV-52` Messaging abstraction
- `INV-53` Message reliability
- `INV-54` Broker implementations
- `INV-55` Secrets integration
- `INV-56` Distributed stateful compute
- `INV-57` Durable execution
- `INV-58` Existing service-mesh layer
- `INV-59` Application authorization
- `INV-60` Wasm application fabric
- `INV-61` Distributed WIT RPC
- `INV-62` Edge topology
- `INV-63` Wasm deployment manager
- `INV-64` Application model
- `INV-65` Capability providers
- `INV-66` Enterprise Wasm control plane
- `INV-67` Kubernetes integration mechanism
- `INV-68` Resource packing
- `INV-69` Agentic workload layer
- `INV-70` Fast agent sandbox
- `INV-71` Heavy agent sandbox
- `INV-72` Accelerated workload requirement
- `PLN-01` Intent plane
- `PLN-02` Application plane
- `PLN-03` Distributed runtime plane
- `PLN-05` Elasticity plane
- `PLN-06` Data plane
- `SCH-01` Workload Classification and Runtime Placement Engine

A component resolves its siblings at run time through `pk_core.integration`. If a
dependency is *not* installed, the affected requirement is reported `partial`
naming the missing element rather than claiming an integration that is not there,
so this payload reports honestly in a full or a partial install.

## Layout

- `pk_core/` -- contract validation, the W0-W9 workflow engine, the hash-chained evidence ledger, the registry, the conformance gate, and the sibling resolver
- `pk_components/<element>/` -- `contract.py`, `component.py`, `CHECKLIST.json`, `README.md`, and `MASTER.md` for owned elements
- `PK_OWNERSHIP.json` -- which elements this project owns
- `PK_ROUTING.json` -- the estate-wide routing and its reasoning
- `PK_CONDITIONS.md` -- every requirement still recorded `partial`, with why
- `SELFTEST.py` / `tests/` -- the conformance suite, with and without pytest

## Running it

```
cd UC270/pk
python SELFTEST.py
python -m pk_core list
python -m pk_core run --evidence evidence/pk_evidence.jsonl --report reports/PK_WORKFLOW.json
python -m pk_core gate --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## How the gate behaves

The workflow refuses rather than degrades:

- **W0** will not lock context on an incomplete contract.
- **W4** will not integrate an interface that carries no schema reference.
- **W7** will not certify while any requirement is `blocked`.
- **W9** will not close out unless the evidence chain verifies and all 100
  requirements of every element have been answered.

`GO` requires that nothing is partial. This payload returns **`CONDITIONAL_GO`**:
each condition is a requirement deliberately recorded `partial` with its reason
and the element it waits on. `PK_CONDITIONS.md` lists them.

## Day-0 / day-1 / day-2

- **Day 0:** run `python SELFTEST.py`, then `pk_core run` and archive the emitted evidence ledger as the baseline.
- **Day 1:** run `pk_core gate`; `NO_GO` blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2:** re-run the gate on every contract or implementation change and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head. Emergency disable is removal of a
component package, which the gate reports as a reduced element count -- and which
any sibling depending on it will report as a new `partial`, never as a silent pass.
