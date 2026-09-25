# ADR-0001: Firecracker microVM per heavyweight agent session

**Status:** Proposed. Not approved. Approval needs recorded review by the platform, security, SRE, networking and release owners in `governance/approvals/`, and no owner has been assigned (see `docs/OWNERSHIP.md`). The v4.3.0 remediation pass expanded this ADR; it did not approve it.

**Version:** 2 (2026-09-23). Supersedes version 1 (4.2.0), which recorded only the decision and consequences.

## Context

INV-71 holds code the fast sandbox cannot or should not hold: real interpreters, package installs, browsers. The guest workload is untrusted and needs stateful execution, filesystem access and deeper OS integration. It must not reach another session's data, the host, or arbitrary network destinations, and teardown must leave nothing for the next session.

Workload assumptions (PROPOSED): sessions last from seconds to one hour (`session.wall_clock_s` ≤ 86400), use 1–16 vCPU and 128 MiB–64 GiB, and install packages from a small set of allowlisted registries.

## Decision

One Firecracker microVM per session, launched by the jailer, with:

- a read-only, digest-pinned guest kernel and rootfs, plus a fresh per-session writable overlay block device;
- cgroup v2 limits (`cpu.max`, `memory.max`, `memory.swap.max=0`, `pids.max`) and jailer resource limits, with Firecracker rate limiters on block and network;
- a per-session network namespace and TAP device, with host-side nftables default-drop and only capability-bound destination tuples allowed (DNS answers come from a trusted resolver, never the guest);
- a dedicated uid/gid per session, a new PID namespace, Firecracker's built-in seccomp filters, no host devices or mounts, and no debug console;
- a control plane with fencing epochs, idempotent operations, a durable signed audit stream and a verified multi-phase teardown.

`control/runtime_plan.py` renders exactly this launch plan. It is not executed anywhere in this repository.

## Alternatives evaluated

| Option | Isolation | Start time | Density | Why rejected |
|---|---|---|---|---|
| Containers / namespaces only | shared host kernel | fastest | highest | A kernel bug is a cross-tenant escape. That is too weak for untrusted code with package installs and browsers. |
| gVisor | user-space kernel | fast | high | Syscall compatibility gaps for browsers and native packages. It is still a shared-kernel failure domain for the Sentry. Kept as a fallback candidate. |
| Kata Containers | VM (QEMU/CLH/FC) | medium | medium | Adds an OCI/CRI layer we do not need. With the Firecracker VMM it is the same boundary with more moving parts. |
| Full VMs (QEMU/KVM) | VM, large device model | slow | low | The large emulated device surface widens the attack surface and cold starts miss the 250 ms target. |
| WASM (Wasmtime/WAMR) | language VM | fastest | highest | Cannot run arbitrary native interpreters, package managers or browsers. That is the reason INV-71 exists. |
| **Firecracker + jailer** | VM with a minimal device model | ~125 ms class boot (vendor-published; not measured here) | high | **Chosen**: a small device surface, snapshots and a jailer confinement model. |

## Frozen production boundary

VMM: Firecracker + jailer (exact versions UNPINNED). Host: Linux with KVM, unified cgroup v2, nftables, and a kernel baseline per `docs/generated/PROFILES.md`. Guest: a pinned kernel and read-only rootfs. Snapshot model: a clean base snapshot per image digest, with no writable snapshot ever reused. Network enforcement point: host-side, outside the guest. Identity plane: mTLS workload identities from a PKI (not present). Telemetry: GAP-09. Teardown authority: the node agent, verified by reconciliation against observed host resources.

## Quantitative consequences (PROPOSED targets, not measurements)

| Quantity | Target | Evidence today |
|---|---|---|
| create-to-ready, warm snapshot | p99 ≤ 250 ms | none. Not measured, because there is no host |
| per-session VMM memory overhead | ≤ 10 MiB | none |
| host density | set from the capacity model once measured | none |
| snapshot storage | one base per image digest, plus zero reused writable layers | none |
| failure blast radius | one session (VMM crash), one node (host kernel) | failure matrix F04/F15 |
| patch cadence | critical ≤ 72 h, high ≤ 14 d (PROPOSED, `docs/OPERATIONS.md`) | none |

## Residual risks

Host kernel/KVM escape (F15), CPU side channels (SMT is disabled in the plan, but core scheduling and co-tenancy policy are not implemented), and residual data in host memory and storage (INV71-X006). The real boundary is untested.

## Supersession rules

A new ADR with fresh review is required when any of these change: the hypervisor class, the guest kernel major line, the host confinement model (jailer/seccomp/cgroups), or the trust boundary (identity plane, network enforcement point). `tests/test_governance.py` fails if this ADR's status line changes to Accepted without a matching approval record in `governance/approvals/`.
