# Provider matrix (INV-38-C031)

Pinned stack: `platform/rdma-stack.lock.yaml`; qualification:
`platform/hardware-qualification.yaml`; preflight: `platform/preflight.py`.
Supported modes (RoCEv2, InfiniBand, SR-IOV/VF) are all `qualification-required`
until run on physical NICs with IOMMU. Preflight fails **closed to the kernel
path** when the pinned stack or capabilities are absent. **Status:** `BLOCKED` —
hardware/firmware/driver qualification requires physical RDMA NICs + IOMMU.
