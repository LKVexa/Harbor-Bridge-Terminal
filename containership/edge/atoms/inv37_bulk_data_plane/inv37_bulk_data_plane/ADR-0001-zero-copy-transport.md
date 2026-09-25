# ADR-0001 — Bulk data-plane zero-copy transport

**Status:** Proposed — awaiting `architecture_approver` sign-off (governance/APPROVALS.json). The remediation author cannot approve this ADR.
**Date:** 2026-09-22 · **Version:** 4.3.0 · **Supersedes:** ADR-0001 draft of 4.2.0 · **Superseded by:** — (a later ADR must name this one and state which decisions it replaces)
**Deciders (roles):** architecture_approver (A), security_owner (C), service_owner (C), sre_owner (I)
**Scope:** how INV-37 moves verified object bytes between a producer and the receiver without repeated copies. Covers INV-37-C010, C011, C031, C065, C066.

## Context

The checklist names the technology *zero-copy shared memory* and the function *avoid repeated host/guest copies*. v4.2.0 buffered every chunk (`tobytes()`) and assembled with `b"".join`, i.e. two full data-plane copies per object (measured: peak allocation 2.0× object size).

## Options evaluated

| Option | Zero-copy? | Portability | Isolation | Verdict |
|---|---|---|---|---|
| POSIX shm / Windows named sections via CPython `multiprocessing.shared_memory` | Yes, intra-host cross-process | Linux, macOS, Windows; CPython ≥3.8 (3.10 required here) | per-region name + HMAC-bound descriptor; OS page permissions | **Selected (phase 1)** |
| `memfd_create` + fd passing (SCM_RIGHTS) | Yes, intra-host | Linux only | fd capability; sealing (F_SEAL_*) prevents mutation | Preferred phase-2 upgrade on Linux (adds sealing); needs a UNIX-socket control channel |
| mmap-backed file | Yes (page cache) | All | filesystem permissions | Used for the durable checkpoint path (`data.bin`), not for live sharing |
| virtio / vhost-user shared buffers | Yes, host↔guest | Linux/KVM, requires VMM integration | IOMMU + VMM mediated | **Required for the host/guest claim; not implemented** (needs VMM, drivers, pinned versions) |
| ivshmem | Yes, host↔guest | QEMU only | weak (whole-region sharing) | Rejected: no per-transfer isolation |
| vsock + shared buffers | Control only; data still copied | Linux/Hyper-V | good | Rejected as data path; acceptable as control channel |
| RDMA registered memory | Yes, cross-host | needs RNICs | PD/MR keys | Out of scope (INV-38 kernel-bypass transport) |
| io_uring registered buffers | Reduces copies for I/O | Linux ≥5.x | kernel | Deferred: optimises storage/network I/O, not host/guest sharing |

## Decision (phase 1, implemented in 4.3.0)

1. **Ownership model.** The receiver-side data plane allocates one region per transfer (`SharedRegion`), sized to `manifest.size`, bounded by `limits.max_mapped_bytes`. It is the *only* party allowed to unlink. The producer attaches using a descriptor and writes (or generates) bytes in place; attachers unregister from their resource tracker so their exit never reclaims the owner's region (fixes a CPython <3.13 lifetime hazard found during this work).
2. **Descriptor exchange.** `INV37_SHM_DESCRIPTOR/1` = {abi, name, size, transfer_id, tenant, generation, binding}; `binding` = HMAC-SHA256(key, [abi,name,size,transfer_id,tenant,generation]). `attach` requires matching transfer/tenant, a valid binding and a non-revoked generation → prevents confused-deputy and stale mappings.
3. **Lifetime/reclamation.** Region lives from `create_transfer` until `cancel`/`close`/`quarantine`/total-timeout; `revoke()` marks the generation dead and unlinks. Pinning: none (pageable shared memory); memory pressure is bounded by `max_mapped_bytes` and admission.
4. **Verification in place.** The receiver hashes `memoryview` slices of the region (`commit(i)`), and `object_view()` re-hashes all chunks before returning a **read-only** view, so post-commit mutation by a producer is detected (`object_digest_mismatch` → quarantine).
5. **Copy-count contract.** A *data-plane copy* is any duplication of payload bytes inside INV-37 into a new buffer. Hashing is not a copy. The producer's write into the region is the single *ingress copy*, avoidable when the producer generates in place. Measured by `CopyCounter` and independently by `tracemalloc` peak allocation in `benchmarks/bench.py`.
6. **Fallback.** `transport.mode=auto` selects shm when `probe()` reports it, else the copy path with health `degraded` and a `transport_select` decision record. `require_zero_copy=true` or `mode=shm` without capability fails closed (`unsupported_capability`); a host/guest requirement always fails closed in 4.3.0.

## Trust boundaries

Producer and receiver are distinct principals; both authenticate with capability tokens (`attach-buffer`, `write-chunk`). Shared pages are writable by the producer until finalize — the receiver therefore never trusts region contents without re-hashing. Cross-tenant exposure is prevented by per-transfer regions and descriptor binding; there is no region pooling or reuse across tenants. For host/guest (phase 2) the VMM must enforce IOMMU mappings per region and revoke them on close; that is not provided here.

## Portability

| Platform | Phase 1 status |
|---|---|
| Linux x86_64 / aarch64, CPython 3.10–3.13 | Designed; certified only on Linux x86_64 CPython 3.11.15 (sandbox) |
| macOS | Designed (POSIX shm); not certified |
| Windows | Designed (named sections; no unlink semantics — reclaimed on last close); not certified |
| Containers | Requires shared `/dev/shm` between producer and receiver (same pod / IPC namespace) |
| VMs (host↔guest) | Unsupported |

## Criteria before the zero-copy path becomes default in production

- 0 data-plane copies and peak allocation ≤ 1 % of object size (met in sandbox: 0 copies, 0.03 %).
- Throughput ≥ copy path and p99 chunk latency ≤ copy path on target hardware (met in sandbox: ≈198 vs ≈148 MiB/s; p99 2.7 ms vs 3.8 ms, medians of 5 runs).
- Security review of descriptor binding and attach path by `security_owner`.
- Certification on each claimed platform row (multi-arch matrix gate criterion).

## Rejected alternatives and rationale

ivshmem (no per-transfer isolation); vsock data path (copies); pooling one large region for all tenants (cross-tenant exposure risk, complex reclamation); relabelling Python `memoryview` hashing as "zero-copy" without a shared region (would not avoid process/host copies — explicitly prohibited by the remediation rules).

## Consequences

The **intra-host** zero-copy property is implemented and measured. The **host/guest** function named by the checklist remains unimplemented; `C010/C011/C066` stay open for that portion and the production gate criterion `host_guest_zero_copy` is BLOCKED until a phase-2 ADR selects and integrates a virtio/vhost-user (or equivalent) path.
