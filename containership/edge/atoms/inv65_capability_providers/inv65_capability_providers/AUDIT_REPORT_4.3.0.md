# INV-65 Capability Providers — 4.3.0 remediation report

**Input:** `inv65_capability_providers` 4.2.0 (hardened) + `INV65_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST_4.2.0.md` (M01–M40)
**Output version:** 4.3.0 · **Date:** 2026-09-22 · **Gate:** NO_GO (see `conformance/PK_GATE_RESULTS.json`)

## Result

| Disposition | Count | Components |
|---|---|---|
| closed-local | 18 | M03 M05 M06 M08 M10 M11 M12 M13 M14 M15 M16 M18 M24 M25 M31 M35 M38 M40 |
| partial | 18 | M04 M07 M09 M17 M19 M20 M21 M22 M26 M27 M28 M29 M30 M32 M33 M34 M36 M39 |
| blocked | 4 | M01 (MASTER.md absent), M02 (pk_core unsupplied), M23 (adjacent layers absent), M37 (licence is the owner's choice) |

"closed-local" means implemented with passing executable tests and nothing external required. It does **not** mean independently reviewed: no independent reviewer exists for this pass, so no item is claimed accepted.

## Verification performed (all re-runnable)

- Tests: 130 run, 126 pass, 4 skip (3 pk_core conformance; 1 wheel reproducibility under Debian's patched setuptools — passes in a clean venv). Same result under `python -O`.
- Fuzz: 30,000 executions over six targets (authn, config, schema, envelope, WAL, authz), seed 65, **0 crashes**, 0 mutated deny-decisions authorized.
- Benchmarks: full-stack dispatch p99 ≈ 0.5 ms on the build host (SLO: p99 < 1 ms, ≤1% over); cold start of 2,000 durable links ≈ 0.02 s; burst sheds load while a quiet tenant is still admitted. The 10 s soak shows memory still rising (~2.8 MB in its second half before fix 7 below, ~0.75 MB after): that is bounded buffers filling — the replay-nonce cache holds one entry per token until expiry (≤100k) — and a short soak cannot demonstrate the plateau. A long soak is still owed.
- Evidence: `evidence/pk_evidence.jsonl` hash chain verified by `tools/verify_evidence.py`; head recorded in `PK_GATE_RESULTS.json` and `release/manifest.json`.
- RTM: 100 rows, `tools/check_rtm.py` clean — every `verified-local` row cites an existing test, every `partial`/`blocked` row names its blocker.

## Defects this pass found in its own work and fixed

1. **Token malleability** (fuzz): junk characters in a token were discarded by the stdlib base64 decoder, so altered strings still verified. Strict canonical decoding + regression test.
2. **O(n) replay-cache sweep per authentication** (profiling) — would degrade linearly with traffic. Heap-ordered expiry.
3. **Schema re-read from disk on every validation** (profiling). Cached. Items 2–3 took dispatch p99 from a failing ~1.16 ms to ~0.5 ms.
4. **Fuzz generator recursion** — my first generator built every branch eagerly and recursed without bound, reporting 5,970 false "crashes". Fixed in the harness, not by loosening invariants.
5. **Link update denied as "link.create"** — audit/deny labels used the wrong action for updates; fixed and covered.
6. **Release gate verifying a stale evidence chain** — a second gate run would compare the old chain with freshly rewritten artifacts; the gate now removes stale chain/results first.
7. **Unbounded-looking telemetry buffers** (soak): the latency histogram kept up to 100k raw samples and the tracer stopped recording once full. Now a 4,096-sample reservoir and a 2,048-span ring (newest kept).
8. **RTM citing a generated artifact** (chicken-and-egg with the gate) — RTM now cites only sources.

## What must happen before GO

M02 supply and pin `pk_core`, then run the 100-item conformance; M23 run `tests/integration/test_adjacent_layers.py` seams against the real INV-60/55/64/61; name owner + independent reviewer; approve ADR-0001; choose a licence; sign SBOM/provenance/manifest; run the CI matrix; exercise rollout/rollback and mTLS against production-like state.
