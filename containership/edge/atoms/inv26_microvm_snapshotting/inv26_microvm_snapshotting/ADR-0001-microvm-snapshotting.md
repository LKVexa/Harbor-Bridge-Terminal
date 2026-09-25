# ADR-0001 — Snapshot/restore to reduce effective microVM startup latency

**Status:** PROPOSED (approval by accountable, security and operations owners pending — roles unassigned in `ops/ownership.json`)
**Date:** 2026-09-23 · **Controls:** C010 (also C016, C031, C041, C047)

## Context
Cold-booting a microVM costs on the order of 100 ms+ (kernel + init + application warm-up). INV-26's contract
promises a p99 restore under 10 ms. A snapshot contains live guest memory (secrets, RNG state), so the
technique is also the easiest way to leak one tenant's memory into another's process or to clone identical
randomness into many guests.

## Decision
1. Use **full VM snapshot/restore** through the VMM's own snapshot API, behind the narrow `HypervisorPort`.
   Supported adapters: **Firecracker** (primary; snapshot API stable since 1.0, File/UFFD memory backends,
   jailer model) and **Cloud Hypervisor** (secondary). QEMU/KVM is **excluded** for now (much larger device
   surface, migration-stream format instead of a narrow snapshot API; revisit if a workload needs devices
   Firecracker lacks).
2. Architectures: **x86_64** and **aarch64**; a snapshot is only restorable on the architecture, VMM major
   version and device-model fingerprint it was captured on (manifest `runtime` + `fingerprint`).
3. **Snapshot format ownership:** the VMM owns the state/memory file formats; INV-26 owns the envelope
   (`AES-256-GCM-CHUNKED/1`), the manifest (`PK_SNAPSHOT_MANIFEST/1`) and the lifecycle.
4. **Entropy model:** every restore generates a fresh 256-bit seed on the host and delivers it to an in-guest
   agent over vsock with a proof-of-receipt before the guest is resumed; VMGenID (Firecracker ≥ 1.8, x86_64)
   is a complementary kernel signal, not a substitute.
5. **Storage model:** blobs are ciphertext under a per-snapshot DEK wrapped by a KMS KEK; plaintext exists only
   in process memory and the private tmpfs working directory during load.
6. **Tenant boundary:** a snapshot is bound to tenant, workload, environment, site and device model at
   capture; cross-tenant template sharing is a non-goal.

## Alternatives rejected
| Alternative | Why rejected | Reversal criterion |
|---|---|---|
| Cold boot only | misses the latency objective by an order of magnitude | if restore overhead (incl. decrypt) cannot beat cold boot on a class of hardware |
| Pre-booted warm pools | idle cost; a pooled guest still needs per-tenant isolation and reseed | if pool cost < snapshot storage + KMS cost for a workload |
| Process checkpointing (CRIU) | weaker isolation, kernel-version coupling | never for multi-tenant |
| Application-level warm state | outside INV-26's ownership; not general | per-application decision upstream |

## Compatibility-sensitive decisions (irreversible without re-capture)
Snapshot envelope version; device-model hashing (SHA-256 over sorted JSON device IDs); CPU feature masks and
page size (implicit in the VMM state file — a mismatch must refuse, never best-effort); memory backing (File vs
UFFD); host kernel KVM ABI.

## Review triggers
VMM major upgrade; `PK_SNAPSHOT*` major schema change; new CPU architecture; any proposal for cross-site restore
or replication (currently `prohibited` in every tier).

## Consequence discovered while implementing
Measured on the build host (no KVM, reference VMM): INV-26's own overhead is ~3 ms p50 at 1 MiB and ~32 ms p50
at 16 MiB, dominated by AES-GCM and copies. **A 10 ms p99 for multi-hundred-MiB guests is not reachable while
the whole image is decrypted before load** — see BENCHMARKS.md. Under the precedence policy (C019) the
encryption requirement wins over the SLO; the SLO must be re-stated per memory class or the design moved to
lazy, per-page authenticated decryption (UFFD). Recorded as DEBT-1.
