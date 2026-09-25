# CPU / runtime / hypervisor / provider / protocol compatibility matrix (C084)

Machine-readable: `tests/compatibility/matrix.json`; `tests/compatibility/test_matrix.py`
fails if a cell marked `required` has no passing evidence, and runs the cells this host can execute.

| Axis | Cell | Status | Evidence |
|---|---|---|---|
| CPU | x86_64 | **tested** | this repo CI |
| CPU | aarch64 | CI matrix (GitHub `ubuntu-24.04-arm`) | `.github/workflows/verify.yml` |
| Python | CPython 3.11 / 3.12 / 3.13 | 3.11 tested here; 3.12/3.13 in CI matrix | workflow |
| Python | PyPy 3.10 | not supported (`pyproject` requires ≥3.11) | — |
| Hypervisor/VMM | QEMU/KVM vhost-user | **pending** real backend | WVR-002 |
| Hypervisor/VMM | Firecracker / Cloud Hypervisor | **pending** | WVR-002 |
| Datapath | in-kernel vhost-net / vhost-blk | **pending** | WVR-002 |
| Datapath | vDPA | **pending** | WVR-002 |
| Provider | cloud / datacenter / near-edge / far-edge profiles | **tested** (config + semantics) | `test_every_profile_builds` |
| Protocol | PK_VIRTQUEUE_SUBMIT/1, COMPLETE/1 | **tested** | contracts |
| Protocol | virtio 1.x split ring / packed ring semantics | reference model covers split-ring chaining; packed ring **pending** | — |
