# M16 Determinism specification (profile `deterministic`)

A module admitted under the `deterministic` profile MUST produce bit-identical results for identical
inputs on every certified engine and architecture. This element guarantees the *module-side* half:

1. **Instruction set.** Only features whose registry entry has `deterministic: true`
   (`core, mutable-globals-import, sign-ext, sat-float-to-int, multi-value, bulk-memory, reference-types`).
   SIMD relaxed ops, threads/shared memory, and any unregistered proposal are refused.
2. **NaN bit patterns.** Wasm core float ops may return nondeterministic NaN payloads. If a module uses
   any float instruction (`uses_float`), the target engine MUST have `nan_canonicalization: true` in the
   engine registry, or admission is refused (`ENGINE_UNSUPPORTED`).
3. **Host imports.** Only the `pure` import class is allowed; clock/random/scheduling imports are
   `nondeterministic` and imply `wall-clock` where applicable.
4. **Resource exhaustion.** `memory.grow`/`table.grow` failure depends on host limits; engines MUST apply
   the M24 handoff limits identically on all hosts (fuel metering required: `fuel_metering: true`).
5. **Traps** are deterministic in Wasm; stack-overflow depth is engine-defined → M24 handoff pins a
   maximum call depth.

**Engine-side half (M20):** certification requires running a determinism corpus on every
(engine, architecture) pair and comparing outputs bit-for-bit. Not yet executed: this build environment
has a single architecture (x86-64) and no certified engine. Status: OPEN / infrastructure-blocked.
