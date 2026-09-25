# Third-party notices — INV-34 5.1.0

No third-party code is copied into this package. Runtime imports are the Python standard library only.

| Donor (GitHub Junkyard car) | Part(s) consulted | Licence | Use |
|---|---|---|---|
| `cloud-hypervisor` | `vmm/src/api/openapi/cloud-hypervisor.yaml` (API 0.3.0: `GET /vm.info`, `PUT /vm.resize`, `VmResize.desired_vcpus`, `CpusConfig`) | Apache-2.0 (OpenAPI `info.license`) | Pattern only: endpoint names and field shapes implemented by `production/adapters/cloud_hypervisor.py` |
| `cloud-hypervisor` | `vmm/src/cpu.rs` (ACPI CPU hot-plug via CPU manager `CSCN`/`_EJ0`; `max_vcpus: u8`; `resize` also shrinks) | Apache-2.0 AND BSD-3-Clause (SPDX header in file) | Pattern only: informed the 255-vCPU ceiling and the refuse-before-shrink guard |

The donor's root LICENSE files were not present in the yard copy (only directories were listed at the car root);
licence names above are taken from the files' own SPDX header and the OpenAPI document.
