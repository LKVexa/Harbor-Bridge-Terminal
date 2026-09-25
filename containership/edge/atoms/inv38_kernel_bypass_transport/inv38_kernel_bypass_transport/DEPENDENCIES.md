# Dependency and integration notes — INV-38

## Required external core

`pk_core` is required for `contract.py`, `component.py`, the registry/integration resolver, the 100-item assessment engine, evidence emission, and production-gate commands documented in the README. It is intentionally not vendored in this archive. A release bundle must pin and ship (or otherwise reproducibly provide) a compatible `pk_core` revision before the conformance gate can be treated as executable evidence.

## Adjacent components referenced by the contract

- INV-35 — High-performance VM I/O
- INV-36 — Control transport; its `Session` interface is optionally exercised by `assess_security` when resolvable.
- INV-37 — Bulk data plane
- GAP-12 — WAN resilience and NAT traversal

The standalone archive does not include these siblings, integration fixtures, or a compatibility matrix for them.

## Hardware/runtime dependency still unspecified

The checklist names RDMA, but this repository contains a deterministic Python reference model only. It does not pin an RDMA specification, verbs/provider implementation, NIC/driver/firmware combination, DPDK version, io_uring version, IOMMU policy, huge-page configuration, or supported CPU/OS/hypervisor matrix. Those remain production gaps and are itemized in `AUDIT_REPORT.md`.
