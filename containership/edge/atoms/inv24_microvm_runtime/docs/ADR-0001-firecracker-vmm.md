# ADR-0001 — Firecracker as the INV-24 VMM (MC-008)

**Status:** PROPOSED (approval record required — see bottom)  
**Date:** 2026-09-23

## Context
INV-24 must boot single-tenant guests with a closed five-device model
(`virtio-net`, `virtio-block`, `virtio-vsock`, `serial`, `rtc`) inside a
125 ms cold-boot budget, with a small attack surface.

## Options considered
| Option | Device model | Boot | Attack surface | Verdict |
|---|---|---|---|---|
| **Firecracker** + jailer | virtio-mmio minimal set, no PCI (by default) | tens of ms class | small, Rust, seccomp per thread | **Chosen** |
| Cloud Hypervisor | virtio-pci, hotplug, VFIO | fast | larger (PCI, hotplug, VFIO) | Rejected: widens device model |
| QEMU microvm | configurable minimal | fast | large C codebase, easy to widen | Rejected: config can widen surface |
| gVisor / containers | n/a | fastest | shared host kernel | Rejected: not hardware isolation |

## Decision
Use Firecracker through the typed adapter `adapters/firecracker.py`, always
launched via the jailer policy in `security/isolation.py`, with binaries pinned
by SHA-256 in `artifacts/firecracker/manifest.json`.

## Constraints and consequences
- No PCI passthrough, no hotplug, no live migration (matches contract non-goals).
- Adapter whitelists API paths/fields; new Firecracker fields need an ADR amendment.
- Snapshot compatibility is tied to the Firecracker version (MC-004, MC-011).
- The pinned version must be approved; until then launch fails closed (`ARTIFACT_UNPINNED`).

## Approval record
| Approver | Role | Decision | Date |
|---|---|---|---|
| UNASSIGNED | Accountable owner | PENDING | — |
| UNASSIGNED | Security approver | PENDING | — |
