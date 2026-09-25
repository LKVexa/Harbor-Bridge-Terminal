# ADR-0001: Paravirtual virtio-net and virtio-block as the only permitted INV-25 device classes

- **Status:** Proposed (approval PENDING — architecture: `@inv25-owners`, security: `@inv25-security`; W-0002)
- **Date:** 2026-09-23
- **Deciders:** INV-25 component owner, INV-25 security reviewer
- **Supersedes / superseded by:** none

## Context
Every guest-visible register is a potential VM-escape path. Legacy device emulation (PCI/ISA,
IDE, e1000-class NICs) carries a large, historically exploited surface; host passthrough and raw
MMIO hand the guest direct host resources.

## Decision
1. The catalogue permits exactly one class, `paravirtual`. `legacy-emulation`, `host-passthrough`
   and `raw-mmio` are forbidden outright; any other class fails closed (`model.py`).
2. The initial devices are **virtio-net** (guest networking) and **virtio-block** (root/data volume).
3. **Normative specification:** OASIS *Virtual I/O Device (VIRTIO) Version 1.2* (Committee
   Specification), device sections 5.1 (network) and 5.2 (block). Review of any later edition
   requires a superseding ADR.
4. **Transport:** transport selection (virtio-mmio vs virtio-pci) and vhost/vDPA acceleration are
   owned by INV-24/INV-35. INV-25 does not model transport.
5. **Feature-bit negotiation** is delegated to the runtime/backend; INV-25's `registers` set is the
   catalogue's *declared guest-visible surface granularity* — configuration-space fields and
   feature bits the device is allowed to expose, one identifier each. Adding a feature bit or
   config field is a surface widening and needs `replace()` with a new version, a surface diff,
   `catalogue.widen`, and security review.
6. `DeviceSpec.version` is the **internal catalogue surface version**, not the virtio spec version.

## Alternatives rejected
- *Emulated e1000/IDE:* broad legacy surface, no security benefit for microVM workloads.
- *VFIO/PCI passthrough:* exposes host devices directly; breaks the surface model and isolation.
- *Unrestricted virtio device zoo (gpu, sound, input…):* unnecessary surface for the workload class.

## Consequences
- Minimal, diffable surface; all widening is an explicit, audited event.
- Workloads needing other devices are out of scope (non-goal) unless a new ADR admits a class.
- Version changes must be compatibility-checked against INV-26 snapshots (restore rejects surface drift).

## Lifecycle
A new device class, transport assumption in INV-25 scope, or change to register semantics requires
a new ADR that supersedes this one. Referenced from `README.md` and `governance/RTM.json` (C010).
