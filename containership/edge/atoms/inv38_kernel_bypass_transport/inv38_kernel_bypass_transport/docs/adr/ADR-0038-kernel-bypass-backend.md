# ADR-0038 — Kernel-bypass backend (RDMA)

- **Status:** Accepted (2026-09-22) · machine-readable twin: `architecture/rdma-decision-record.yaml`
- **Deciders:** architecture-board, security-architecture-board

## Problem (C010-T01)
INV-38 must place network payloads directly into guest/user memory to hit a p99
post-to-completion target < 5 µs, while preserving end-to-end sealing and DMA
isolation. Every device access must fall inside a registered region.

## Options compared (C010-T02)
RDMA verbs/rdma-core (RoCEv2 & InfiniBand), DPDK-style polling, io_uring/kernel
fallback, and a non-bypass kernel baseline.

## Decision drivers (C010-T03)
Latency, CPU overhead, NIC offload, MR registration cost, IOMMU isolation,
SR-IOV/virtualization support, operational complexity, portability, failure
recovery.

## Decision
RDMA (rdma-core verbs; RoCEv2 primary, InfiniBand where present). Data plane owns
queue pairs, MR registration and completion handling; control plane owns policy
and registration authorization. Fails **closed to the kernel path** when the
pinned stack or hardware capabilities are absent.

## Security consequences (C010-T05)
DMA authority, MR key lifetime and stale-key risk, device reset semantics,
privileged setup isolation, firmware trust and side-channel exposure — tracked in
`security/*` and enforced by `authz.py`/`privilege_check.py`.

## Rejection criteria & rollback (C010-T06/T08)
Unsupported NIC/driver/firmware/IOMMU combinations are rejected by
`platform/preflight.py`. Rollback is the kernel-path baseline plus the previous
sealed evidence head.

## Status against C010
`IN_PROGRESS` — the ADR is approved and versioned; the backend benchmark evidence
required by C010-T07 needs RDMA hardware (see C061, BLOCKED).
