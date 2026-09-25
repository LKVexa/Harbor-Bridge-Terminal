# ADR-0001 — SFI production profile `PK-SFI-WASM32-MVP-1`

| Field | Value |
|---|---|
| Status | **PROPOSED** (not approved — approvers in `OWNERSHIP.md` are UNASSIGNED) |
| Date | 2026-09-22 |
| Scope | INV-45 production enforcement layer (`production/`) |
| Supersedes | nothing; the 4.2.0 Python reference model stays as `sfi_core.py` (reference only) |
| Supersession rule | any change to the pinned items below requires a new ADR that supersedes this one |
| Covers | C010, C031 (and A3) |

## Context

4.2.0 contained only a Python reference model. The checklist requires the actual enforcement boundary:
a rewriter/validator over the exact executable bytes and a trusted loader. The component's declared function
is to strengthen *multi-tenant Wasm execution*, so the enforcement point chosen is the **WebAssembly
binary**, before it reaches the engine.

## Decision — pinned profile

| Item | Pinned choice |
|---|---|
| Execution target | WebAssembly binary format version 1 (MVP) + sign-extension ops + non-trapping float-to-int (0xFC 0–7). Everything else (SIMD, threads/atomics, shared memory, bulk memory, reference types, multi-value, multi-memory, memory64, exceptions, tail calls, GC) is rejected. |
| Rewriting stage | Ahead of load, on the submitted binary (`production/sfi.py::rewrite`). |
| Validation stage | Independent re-parse + full type validation + pattern proof of the rewritten bytes (`production/sfi.py::verify`), repeated by the trusted loader (defence in depth). |
| **Linear block partitioning** | Linear memory is divided into tenant partitions `[base, base+2^k)`, `12 ≤ k ≤ 31`, each followed by an 8-byte dead guard; partitions of co-resident tenants SHALL NOT overlap including guards. |
| **Heap masking** | `addr' = ((addr + offset) mod 2^32 & (2^k − 1)) + base`, offset folded, memarg offset set to 0; integer width i32; wrap-around is defined (confine, not trap). Statically known addresses are folded at rewrite time and re-proven (`base ≤ E ≤ base + 2^k − 1`). |
| Legal branch destinations | Wasm structured control flow (labels only; validated). Indirect calls only via the module's own table, `min == max`, not imported/exported; `permitted_indirect_targets` = element segment functions. |
| **Pinned base register** | Engine responsibility. At the Wasm level the partition base is an immutable immediate in every mask sequence; no guest instruction can change it. Native register reservation is **delegated to the engine** (V8 keeps the memory start in a reserved register) and is **not verified by this component** — recorded as residual risk R-03. |
| **Shadow stack / return integrity** | Provided by Wasm semantics: return addresses live in the engine-managed call stack, not in linear memory; guest code has no instruction to read or write them. No additional shadow stack is implemented. Engine correctness is an external prerequisite (R-04). |
| **Code-page ASLR / W^X** | Engine responsibility (V8 JIT code-space W^X and randomisation). This component enforces "no runtime code generation" on the host (`--disallow-code-generation-from-strings`) and denies filesystem writes to the executing process (Node permission model). Not independently verified (R-05). |
| Engine | V8 via Node.js major 22 (supported 20/22/24) under `--permission`, one process per execution job. |
| Crypto | Descriptor MAC: HMAC-SHA256. Artifact statements: Ed25519 (`cryptography` ≥ 41,< 47). Digests: SHA-256 over exact bytes; canonical JSON (sorted keys, no whitespace, UTF-8, no NaN). |
| Language/runtime of the verifier | CPython ≥ 3.10, standard library only (plus `cryptography` for Ed25519). |

## Upgrade procedure

An upgrade of any pinned item (Wasm feature set, engine major, crypto library major, mask formula) requires:
new ADR → fixture regeneration with reviewed diff → full CI including V8 escape suite and fuzz campaign →
perf gate against the previous baseline → canary per RUNBOOKS.md §Rollout → rollback plan recorded.

## Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Rely on engine bounds checks only | Gives *module*-level isolation, not *partition*-level isolation inside a shared memory; the multi-tenant co-residency requirement (S-FUN-03) is not met. |
| Masking with `base \| (addr & mask)` (OR) | Requires base aligned to the partition size, wasting up to 50 % of the address space for mixed sizes; ADD with guard allows 8-byte-aligned bases. Performance is identical. |
| Trapping on out-of-partition addresses (bounds check instead of mask) | Adds a branch per access and a new trap path; masking is branch-free and matches the reference model's `confine` semantics. |
| Native-code SFI (NaCl-style, x86-64 segment/masking, LFI) | Requires a per-architecture machine-code verifier and loader; out of scope for the declared Wasm function and would duplicate the engine's JIT. Revisit only with a new ADR if a native tier is added. |
| Accepting bulk-memory / threads | `memory.copy/fill` and atomics take addresses the mask sequence does not cover; shared memory introduces concurrent guest mutation. Rejected until the rewriter and verifier cover them. |
| Leaving the parser permissive and letting V8 decide | Parser differentials are an escape vector; the verifier must be at least as strict as the engine (fuzz invariant 3). |

## Compatibility constraints

* `pk_core`: the 100-item checklist binding (`component.py`) still requires the external `pk_core`; it is
  optional for the production layer (package imports without it since 4.3.0).
* INV-44 Wasm hardening system composes these primitives; INV-39 process sandbox is exercised through the
  per-job Node process; INV-30 capability hardware and GAP-02 discovery have no interface in this release.
* Loader/runtime interface: only `SfiService.load(token, bytes, descriptor)`; there is no raw-bytes entry point.

## Consequences / residual risks

R-01 worst-case load-bound overhead ≈ 36 % exceeds the 15 % contract SLO (PERFORMANCE.md) ·
R-02 guard is only 8 bytes, so any future access wider than 8 bytes (SIMD) must not be admitted without a new ADR ·
R-03/R-04/R-05 engine-delegated properties are not independently verified · R-06 single profile per service
instance (per-tenant partition assignment is configured per instance, not negotiated).
