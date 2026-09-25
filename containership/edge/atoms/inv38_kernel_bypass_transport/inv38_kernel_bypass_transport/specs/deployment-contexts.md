# Deployment contexts (INV-38-C012)

Normative capability profiles for datacenter, cloud VM, near-edge and far-edge.
Machine-readable: `specs/deployment-contexts.yaml`. Each profile fixes NIC/IOMMU
assumptions, memory ceilings, RDMA availability (mandatory/preferred/unsupported)
and permitted fallback. The **same external `PK_BYPASS_*` contract holds across
profiles** even when the fast-path differs (C012-T08); conformance is asserted in
`tests/test_deployment_contexts.py`. **Status:** `IN_PROGRESS` — real per-context
NIC/SR-IOV conformance needs hardware.
