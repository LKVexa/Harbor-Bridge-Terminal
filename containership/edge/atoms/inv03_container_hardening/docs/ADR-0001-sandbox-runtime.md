# ADR-0001 — Mandatory user-space-kernel sandbox (gVisor/runsc) for all tenant workloads

- **Status:** PROPOSED (not approved — needs the accountable owner in OWNERSHIP.md; checklist item 56)
- **Date drafted:** 2026-09-22

## Context
INV-03 4.2.0 checked five container flags but let a workload run on the host kernel through `runc`.
A kernel exploit from a hardened-but-shared-kernel container is still a host compromise.

## Decision (proposed)
Every tenant pod must set `runtimeClassName` to an approved sandbox class (default `gvisor` → handler
`runsc`). The `sandbox-runtime` control is not waivable by exception. System workloads are carved out
only by the namespace label `inv03.exempt-system` on the webhook, which itself needs security-admin review.

## Alternatives considered
1. **Kata Containers (VM isolation)** — stronger boundary, higher start latency and node requirements (nested virt).
2. **runc + seccomp/AppArmor only** — 4.2.0's position; shared kernel remains the trust boundary.
3. **Per-tenant node pools** — isolates tenants from each other but not a workload from its node.

## Consequences
- Syscall compatibility: some workloads (e.g. raw sockets, some io_uring use) fail under gVisor and need a Kata class or redesign.
- Performance overhead on syscall-heavy workloads; must be measured (checklist item 52, BLOCKED on a fleet).
- Rollback: install a baseline whose `sandbox_runtime_classes` adds the previous class via a signed baseline + `rollback()`;
  overlays cannot loosen it, so rollback is a deliberate signed act, never an overlay.

## Trust boundary
Admission (INV-03) decides; the node agent attests the handler and version; drift reconciliation compares both.
