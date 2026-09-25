# Adversarial review of the verifier — 2026-09-22

**Reviewer:** an AI sub-agent run inside the same work session, instructed to break `sfi.verify` without
editing the repository. **This is not an independent human security review** and does not satisfy the
reviewer/approval requirement of the completion standard (C041/C087 stay `engineered_unreviewed`).

**Method:** dozens of hand-built modules executed in real V8 (Node v22.22.2) through the engine adapter with
canary-filled shared memory, plus a parser-vs-V8 differential battery.

## Result: no bypass, no exploitable differential

Held (all tested): control-flow edges into or around mask sequences (block/loop/if/else/br/br_table),
`select`-produced and dead-code addresses, wrong mask, `i32.or` for `i32.and`, `local.tee` store values,
constant-value stores in the dynamic form, the "two consecutive constants" store form (the deeper constant is
the range-checked address, matching V8 stack order), 12 verified store variants × 7 hostile addresses,
5-byte `i32.const` encodings (every accepted encoding decodes to the value V8 executes), bulk-memory ops,
`memory.grow`, table/global/memory import-export policy, data segments outside/straddling/guard/negative,
`global.get` offsets, undersized memories, section/body size and order rules.

Every parser/V8 divergence found is fail-closed (we reject, V8 accepts): padded reserved memory index on
`memory.size`/`memory.grow`, typed `select`, `memory.grow` (policy).

## Findings acted on

1. **The 8-byte guard is load-bearing and inter-tenant spacing was not checked.** A top-of-partition
   `i64.store` writes into `[base+size, base+size+8)` and no further (confirmed). Two profiles placed
   back-to-back without the guard would let tenant A corrupt up to 7 bytes of tenant B.
   → Added `production/sfi.py::check_partitions` and the V8 test
   `test_guard_is_load_bearing_and_adjacent_partitions_refused`; W-04 stays open until a central allocator
   calls it for every co-resident placement.
2. **Standing assumption:** the guarantee depends on our decoder seeing the same instruction boundaries as
   the engine (differential fuzz lane keeps testing it).
3. **Engine-delegated properties** (W^X, base register, protected call stack) are out of scope by design
   (ADR-0001, W-08).
