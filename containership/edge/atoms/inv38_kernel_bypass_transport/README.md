# INV-38 - Kernel-bypass transport

**Version:** 4.2.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** not included in this standalone archive; the prior README reference to `MASTER.md` was incorrect.

Kernel-bypass transport hands network or storage queues straight to user space, skipping the kernel copy. The speed comes from the application touching device-visible memory directly, which is exactly the danger: every access must fall inside a registered region, and the sealed end-to-end channel above it must not be weakened just because the path got faster.

## Responsibility

Own the bypass fast path: memory region registration, bounds-checked descriptor posting, completion rings, and transparent fallback to the kernel path when bypass is unavailable.

## Owns

- Memory region registration and keys
- Bounds checks on every posted descriptor
- Submission and completion rings
- Fallback to the kernel path
- Keeping end-to-end sealing above the bypass layer

## Explicitly does not own

- Control semantics
- Chunk verification
- Device drivers
- Placement
- Key custody

## Non-goals

- Writing device drivers
- Verifying payloads
- Weakening encryption for speed

## Interfaces

- `complete` - PK_BYPASS_CQ/1 - a completion entry
- `post` - PK_BYPASS_POST/1 - a descriptor posted against a region
- `register` - PK_BYPASS_MR/1 - a registered memory region and its key

## Service-level objectives

- **memory safety** - zero device accesses outside registered regions (error budget: no budget)
- **sealing preserved** - the fast path carries only sealed frames (error budget: no budget)
- **latency** - p99 post-to-completion under 5us (error budget: 1% may exceed)

## Running it

```
python inv38_kernel_bypass_transport/tests/test_transport.py   # standalone queue safety tests
python inv38_kernel_bypass_transport/tests/test_repository.py  # archive/repository integrity tests
python inv38_kernel_bypass_transport/tests/test_component.py   # requires pk_core; set PK_CORE_PATH if elsewhere
python -m pk_core list
python -m pk_core run INV-38 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-38 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Reference-model hardening

The dependency-independent `transport.py` model now validates address-space ranges and constructor limits, bounds registered regions/submission/completion capacity, snapshots mutable payloads before asynchronous completion, prevents memory-region deregistration while descriptors are in flight, emits stable error codes, and serializes queue mutations with a re-entrant lock. These are model-level safety properties; they are not a substitute for an actual RDMA/DPDK/io_uring device adapter, IOMMU enforcement, production telemetry, or hardware certification.

`pk_core` is an external dependency and is not carried in this archive. The package now degrades explicitly when it is absent: the standalone transport remains importable, `PK_CORE_AVAILABLE` is `False`, and `build_contract()` raises `CoreUnavailableError`. The 100-item conformance assessment still cannot be independently certified from this ZIP unless a compatible `pk_core` and required sibling components are supplied.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-38`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-38`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.
