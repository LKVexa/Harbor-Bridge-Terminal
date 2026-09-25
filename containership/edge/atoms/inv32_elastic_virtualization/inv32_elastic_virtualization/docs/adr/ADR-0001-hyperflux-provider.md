# ADR-0001 — HyperFlux / provider architecture

- Status: **PROPOSED — BLOCKED** (needs accountable owner + approved HyperFlux specification)
- Date: 2026-09-22 · Re-review: on any major provider/protocol/state-model change, and no later than 2027-03-22
- Controls: INV-32-C010, C031

## Problem
INV-32 must drive live memory/vCPU changes through a hypervisor. The v4.2.0 candidate names "HyperFlux" but
ships no specification, version, SDK or transport. Implementing against a guessed API would be unsafe.

## Constraints
Host reserve and guest floors may never be crossed; every mutation must be idempotent, fenced, auditable and
reconcilable after a crash; unknown outcomes must never be blindly retried.

## Options considered
1. Direct library binding in-process — lowest latency; widest blast radius (provider crash = controller crash).
2. Local daemon over a UNIX socket with mTLS-equivalent peer credentials — isolates faults; one hop.
3. Remote RPC (gRPC) — needed only if control is off-host; adds a network partition mode.
4. Kernel/device interface (e.g. virtio-mem/balloon control via VMM API) — provider-specific.

## Decision (proposed)
Transport-neutral `HypervisorAdapter` (implemented). Preferred production form: **option 2** local daemon,
pending owner approval. The production adapter stays fail-closed until `PINNED_SPEC` carries the approved spec
ID and SHA-256 digest and `SUPPORTED_PROVIDER_VERSIONS` is populated from the compatibility matrix.

## Consequences
Controller logic is fully exercised against the deterministic fake; real-provider latency, partial-failure
modes and capability matrix remain unmeasured until the spec lands.

## "Microsecond-scale" budget
Measured controller-owned policy decision latency: p50 ≈ 29 µs, p99 ≈ 70 µs (evidence/bench-results.json,
`decision_only`). The durable path (fsync'd journal + audit) is millisecond-scale by design; provider and guest
cooperation latency are outside this component. Microsecond-scale *reassignment* end-to-end therefore depends on
the provider and on accepting a non-durable fast path, which this ADR does **not** approve.

## Failure assumptions / rollback
Provider may time out after applying; may apply partially; may restart and lose requests; may report wrong
values (verified by re-read). Rollback of this decision = keep the fake/reference adapter and disable mutation.
