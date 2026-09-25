# ADR-0001 — Execution-tier semantics, trust-class floors and provider choices

Status: PROPOSED — awaiting approval by the PLN-04 owner (ops/OWNERS.json: UNASSIGNED)
Date: 2026-09-23 · Supersedes: none · Controls: PLN-04-C010, PLN-04-C031

## Context

The source function reads "Wasm → process sandbox → unikernel → Firecracker microVM → full VM, selected according to workload needs". PLN-04 4.2.0 shipped `TIERS = (process, wasm, unikernel, microvm, vm)` as weakest→strongest, with the trust-class floors below. No ADR ever approved either ordering.

## Decision 1 (open): order of `process` and `wasm`

| Option | Order | Argument |
|---|---|---|
| **A — keep 4.2.0 (recommended)** | process < wasm < unikernel < microvm < vm | The ordering is by *isolation strength*. A bare process under rlimits shares the host kernel's full syscall surface. A Wasm sandbox has no ambient authority, bounded linear memory and fuel. So Wasm is the stronger boundary. The source list reads as an ordering by *weight/start-up cost*, not strength. |
| B — literal source order | wasm < process < … | Matches the source text verbatim. It would let `trusted` land in Wasm and move `first-party` onto a bare process, which weakens isolation for first-party code. |

Option A is implemented. Choosing B means changing `runtime.TIERS`, `TRUST_CLASSES`, the schemas' enum order (the enum *order* is not semantic) and `TIER_HARDWARE_REQUIREMENTS`, then re-running the full suite.

## Decision 2: trust-class floors

| Trust class | Floor | Co-residency default |
|---|---|---|
| trusted | process | shared |
| first-party | wasm | shared |
| third-party | unikernel | shared |
| untrusted | microvm | tenant-exclusive |
| hostile | vm | dedicated node |

## Decision 3: provider choices (to pin)

| Tier | In-tree | Production choice to pin |
|---|---|---|
| process | `ProcessProvider` (rlimits, session, empty env, private scratch) | Add seccomp/landlock or run under a sandbox wrapper before accepting anything above `trusted`. |
| wasm | `WasmProvider` (wasmtime CLI, fuel, memory cap, no preopens) | wasmtime version: _to pin_ |
| unikernel | `CommandProvider` driver | Unikraft/OSv driver: _to choose_ |
| microvm | `CommandProvider` driver | Firecracker version + jailer: _to pin_ |
| vm | `CommandProvider` driver | QEMU/KVM or Cloud Hypervisor with SEV-SNP/TDX: _to choose_ |

## Consequences

- Reference providers are refused by the production profile, and the registry never falls back implicitly.
- A tier is offered only when its provider probe succeeds, discovered hardware meets `TIER_HARDWARE_REQUIREMENTS`, and fresh attestation verifies.

## Approval

| Role | Name | Date | Decision |
|---|---|---|---|
| Owner | UNASSIGNED | | |
| Security reviewer | UNASSIGNED | | |
