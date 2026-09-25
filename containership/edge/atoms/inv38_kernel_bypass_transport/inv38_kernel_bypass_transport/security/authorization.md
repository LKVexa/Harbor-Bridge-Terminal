# Authorization & capabilities (INV-38-C024)

Explicit capability model (register/deregister/post/poll/configure/drain/reset/
diagnose/administer) mapped to principal classes and tenant/workload scope
(`security/capabilities.yaml`, `authz.py`). MR keys are bound to
(tenant, workload, device, generation, access-direction); cross-tenant reuse and
stale generations are rejected (`check_key`). Reset/administer require step-up.
Denial tests in `tests/test_authz.py`. **Status:** `IN_PROGRESS` — OS/device-layer
enforcement (VF/IOMMU group) needs hardware.
