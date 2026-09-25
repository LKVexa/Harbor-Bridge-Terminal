# GAP-11 Accelerator Scheduling — Audit Report

**Input version:** 4.1.0  
**Audited version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** supplied `gap11_accelerator_scheduling` archive only

## Executive summary

The supplied v4.1.0 package had a sound fail-closed intent for whole-device allocation and cross-tenant scrubbing, but its state model did not fully implement the partition semantics claimed by the contract. The largest defect was the single `holder` tuple on each physical device: it could not represent independent declared partition leases, did not distinguish partition capacity from whole-device capacity, and had no lease identity for safe release. The implementation also lacked atomic concurrency protection and stable machine-readable errors.

v4.2.0 separates the allocator into a stdlib-only module, introduces explicit leases and partition capability declarations, adds a physical-device tenant security epoch, makes allocation/release/scrub transitions atomic inside one process, validates inventory and requests, adds accelerator kind matching, reduces default inventory data exposure, and adds a standalone 16-test unit suite.

This audit does **not** classify the package as a complete production control plane. The remaining system components are listed in `MISSING_COMPONENTS.md`.

## Supplied package findings

### Critical / high defects fixed

1. **Partition state was not actually modeled.** One `holder` tuple represented a whole physical device even when a partition name was requested. v4.2.0 uses independent `AllocationLease` records and allows distinct declared partitions to be occupied concurrently by the same tenant.
2. **Partition requests inherited whole-device memory.** A named slice on an 80 GB device could satisfy an 80 GB-style physical memory check without evidence that the slice contained that memory. v4.2.0 requires `PartitionSpec.memory_gb` for positive partition-memory guarantees.
3. **Release identity was ambiguous.** Release accepted only a device name. With true partition concurrency that is unsafe. v4.2.0 emits 128-bit lease IDs and fails closed on device-only release when multiple leases are active.
4. **No concurrency serialization existed.** Two threads could race through check-then-assign logic. v4.2.0 wraps pool state transitions in an `RLock`; the test suite proves that one partition cannot be concurrently allocated twice through the pool API.
5. **Cross-tenant partition co-residency semantics were implicit.** v4.2.0 introduces a physical `security_tenant` epoch that persists until a successful scrub, so separate partitions cannot silently cross tenant boundaries.
6. **Accelerator type was not represented.** The checklist describes GPU/NPU/FPGA resources, but allocation only matched generation, memory, and features. v4.2.0 adds `kind` matching.
7. **Public error semantics were unstable strings only.** v4.2.0 adds stable error codes and structured safe details.
8. **Contract/source-of-truth wording contradicted same-tenant dirty reuse.** The contract previously said a device was free only when scrubbed even though the code allowed same-tenant reuse. The source-of-truth definition now distinguishes lease availability from cross-tenant scrub eligibility.

### Medium defects / hardening fixes

9. Empty tenant/workload, invalid memory, invalid features, duplicate device IDs, duplicate partition names, partition memory larger than physical memory, and impossible known partition-memory totals now fail validation.
10. Failed scrub quarantine remains fail-closed; successful scrub is prohibited while leases are active.
11. Allocation marks the device dirty as soon as tenant execution starts rather than only after release, which better represents the physical security state.
12. Inventory no longer emits the tenant security epoch by default; sensitive tenant identity requires `include_sensitive=True`.
13. The contract now includes the release schema and explicit peer dependencies on identity/attestation and observability.
14. The README falsely stated that `MASTER.md` was bundled. It was not in the supplied archive. The claim is removed and the missing artifact is tracked explicitly.

## Compatibility decisions

- Existing string partition declarations remain accepted for source compatibility.
- A string-only partition has **unknown capacity** and therefore may only satisfy a zero-memory partition request. This is intentionally fail-closed.
- `AcceleratorPool.release("device")` remains compatible when exactly one lease exists. When multiple leases exist, callers must provide `lease_id` (or another selector resolving to exactly one lease).
- Same-tenant reuse after release remains allowed without a scrub because the contract only mandates scrub before a physical device crosses tenants.

## Validation performed

- `python -m py_compile` on all Python sources.
- `tests/test_allocator.py`: 16/16 passing under the standard interpreter.
- `tests/test_allocator.py`: 16/16 passing under `python -O`.
- Race test: 16 concurrent attempts for one partition produce exactly one allocation and 15 refusals through the pool API.
- `CHECKLIST.json`: parsed successfully and contains exactly 100 unique checklist IDs.
- Version pins checked for `VERSION`, `__version__`, README, changelog, and conformance test.

## Validation limitation

The supplied archive does not contain the sibling `pk_core` package. Therefore the full `tests/test_component.py` 100-item framework evaluation cannot be executed in isolation from this archive. The test remains present and version-pinned for execution in the parent series where `pk_core` is available. This limitation is recorded rather than treated as a pass.

## Residual risk

The reference allocator is in-memory and single-process. The `RLock` prevents races only among callers using one `AcceleratorPool` instance. It does not provide distributed fencing, durable recovery, multi-controller split-brain prevention, real hardware reset/zeroization, authenticated transport, policy authorization, or operator-grade telemetry. Those are production requirements, not minor refinements; see `MISSING_COMPONENTS.md`.
