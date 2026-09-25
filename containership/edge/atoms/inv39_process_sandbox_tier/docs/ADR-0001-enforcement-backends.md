# ADR-0001 — Enforcement backends for the process sandbox tier (MC-002)

**Status:** Proposed (implemented; approval by the accountable owner pending)  **Date:** 2026-09-22

## Context
INV-39 must apply default-deny syscall filtering, capability minimisation and namespace isolation, and must *prove* it before workload code runs. The 5.0.0 archive verified caller-supplied read-back only.

## Decision
1. **Linux primary backend: native launcher** (`linux/launcher.py`) — stdlib Python + libc via ctypes: seccomp-BPF compiled in-repo, `unshare` for user/pid/mount/net/ipc/uts, capability bounding/ambient/capset, securebits, rlimits, fd closure, env allow-list, optional Landlock, fresh `/proc`. Chosen because it can gate `execve` on **kernel read-back from `/proc/<pid>`** taken while the workload is blocked after seccomp installation — no other option gave us a pre-exec verification point without a helper binary.
2. **Linux secondary backend: bubblewrap** (`backends.bwrap_argv`) — for nodes that require read-only root, `/dev` minimisation and `pivot_root`; our compiled seccomp program is passed via `--seccomp FD`. Read-back for this path is weaker (bwrap owns the exec), so it is secondary.
3. **macOS: Seatbelt via `sandbox-exec`** (`backends.seatbelt_profile/argv`) — default-deny SBPL. No read-back API exists; evidence is `launcher_attested`. `sandbox-exec` is deprecated by Apple; accepted as the only in-OS option short of the Endpoint Security / virtualization frameworks.

## Rejected alternatives
| Option | Why rejected |
|---|---|
| libseccomp + python bindings | extra native dependency; our 40-line compiler is exhaustively checked by an in-test cBPF emulator |
| Docker/runc/crun | image-format and daemon scope are explicit non-goals of this tier; adds a privileged daemon |
| gVisor / Firecracker | different tier (stronger isolation) — PLN-04 routes hostile code there |
| nsjail / minijail | good tools, but a second supply chain and no hook for our pre-exec read-back gate |
| Namespace-only confinement | explicit contract non-goal: no seccomp → full kernel surface |

## Consequences
Shared kernel remains the residual risk (stated in every applied record). Seccomp rule contents are launcher-attested (MC-047). macOS certification needs a real macOS runner.
