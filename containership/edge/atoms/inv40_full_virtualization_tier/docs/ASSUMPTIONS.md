# INV-40 assumptions (INV-40-C005)

Each assumption names what breaks if it is false and where it is checked.

| # | Area | Assumption | Checked by | If false |
|---|---|---|---|---|
| A-N1 | Node | x86-64 host exposes `vmx` or `svm` and `/dev/kvm` read-write to the tier identity | `fvt/provider.py::HostProbe` on every boot and in `health()` | tier refuses (`PK_FULL_VM_PRIMITIVE_REQUIRED`), readiness false, never emulates |
| A-N2 | Node | Host kernel ≥ one that supports KVM + QEMU `-sandbox` seccomp | not checked in-repo (blocker HW-KVM) | QEMU launch fails → `PK_FULL_VM_GUEST_START_FAILED` |
| A-N3 | Node | `/proc/<pid>/status` VmRSS reflects hypervisor resident size | `provider.rss_mib` | footprint under-reported; SLO "footprint honesty" at risk |
| A-R1 | Runtime | CPython ≥ 3.10, stdlib only for runtime + `fvt/` | `pyproject.toml`, CI matrix | import failure |
| A-R2 | Runtime | `pk_core` present only for the integration component | `fvt/compat.py::check_pk_core` | integration unavailable; standalone runtime unaffected |
| A-R3 | Runtime | Guest OS is opaque and possibly hostile | contract `guest_os_opaque=True`; no guest introspection code exists | — |
| A-W1 | Network | Guest networking is QEMU user-mode with `restrict=on` until a site network adapter is bound | `QemuKvmProvider.argv` | guest has no egress (safe default) |
| A-W2 | Network | Control-plane links may partition; the tier never assumes a peer is reachable | fencing epochs, offline_mode=fail_closed | stale controllers rejected |
| A-S1 | Storage | Guest disks are attached read-only by digest unless a writable volume is explicitly granted | `argv` uses `readonly=on` | — |
| A-S2 | Storage | `state_dir` is on a local filesystem with working `fsync` and atomic `rename` | journal/config/audit use fsync + `os.replace` | crash consistency not guaranteed (documented, not detected) |
| A-C1 | Control plane | INV-33 holds the cross-node lease; this repo's `LeaseTable` is process-local | `fvt/fencing.py` docstring, blocker DIST-STORE | split-brain protection limited to one process |
| A-C2 | Control plane | PLN-04 admits only hostile-class workloads to this tier | not enforceable here (upstream) | cost of tier paid by default workloads |
| A-C3 | Control plane | A KMS/IdP issues capability-token keys | `identity.KeyProvider` interface; blocker SEC-KMS | tokens cannot be issued in production |
