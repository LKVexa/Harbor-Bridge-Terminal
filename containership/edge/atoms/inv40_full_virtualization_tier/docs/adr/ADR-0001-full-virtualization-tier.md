# ADR-0001 — Full virtualization tier on KVM + QEMU (status: **PROPOSED**)

*Decision owner:* UNASSIGNED · *Approved:* no — approval is a human act (INV-40-C010).

## Context
INV-40 exists for *maximum legacy compatibility and compliance isolation*: guests
whose OS is foreign or hostile and that need a complete machine (own kernel,
full device model). The source series names "EC2/QEMU-style full VMs".

## Decision (proposed)
1. Hypervisor: **Linux KVM** as the hardware primitive, **QEMU** (`qemu-system-x86_64`,
   machine `q35`) as the VMM, driven over **QMP**. Adapter: `fvt/provider.py::QemuKvmProvider`.
2. Acceleration is `-accel kvm` only; TCG is never passed. Absent KVM ⇒ refusal.
3. QEMU runs with `-sandbox on,…=deny`, `-nodefaults`, user-mode network `restrict=on`, read-only disks.
4. Full baseline device model (runtime `FULL_DEVICE_MODEL`) is mandatory; extra devices additive only; GPU passthrough off by policy.
5. Cloud (EC2) is modelled as a future second `Provider`; not implemented.

## Alternatives considered
* **Firecracker / Cloud Hypervisor** — microVM device minimalism is an explicit non-goal (belongs to the microVM tier).
* **Xen/HVM** — viable; rejected for tooling footprint in this series.
* **TCG fallback** — rejected by contract: it does not deliver the boundary.

## Consequences
Seconds-scale boots and hundreds-of-MiB footprints are stated, accounted (`boot_ms`, VmRSS) and bounded (budget, ceiling). Version pinning of QEMU/kernel is open (INV-40-C031, blocker HW-KVM).
