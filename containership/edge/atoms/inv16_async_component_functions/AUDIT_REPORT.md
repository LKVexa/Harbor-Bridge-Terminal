# INV-16 Post-Closure Audit Report

**Audited version:** 4.3.0 (from hardened 4.2.0)
**Audit date:** 2026-09-23
**Driver:** `INV16_v4.2.0_Missing_Components_Closure_Checklist.md` (42 components)
**Item-by-item status:** `docs/CLOSURE_LEDGER.md` (generated from `tools/closure_status.py`)
**Machine-readable evidence:** `evidence/` — verify with `python tools/verify_evidence.py`

## Verification performed (numbers in `evidence/INV16_LOCAL_GATE.json`)

- `compileall` on the whole tree.
- Full suite (15 files, 110 tests) on CPython 3.10, 3.11, 3.12 and 3.13, each in normal and `-O` mode —
  logs and per-run digests in `evidence/test_matrix.json` / `evidence/logs/`.
- The three `pk_core` conformance tests are skipped (pk_core absent) and are **never** counted as PASS.
- Stdlib lint + security rules (`evidence/lint.json`), line-coverage gate with critical lifecycle functions
  fully covered (`evidence/coverage.json`).
- Bridge-cost benchmark with raw samples, capacity benchmark, multi-minute soak (`evidence/bench/`).
- Reproducible wheel + sdist (byte-identical rebuild), CycloneDX SBOM, in-toto/SLSA provenance, checksum
  manifest, clean `pip install --target` smoke test (`evidence/release/`, `evidence/clean_install.json`).
- Executed rollback (4.3.0 → 4.2.0 with in-flight and terminal state) and canary promotion/abort.
- Preflight in normal mode and in certification mode (`--require-pk-core`, expected to fail closed here).

## Defects found during the closure work (all fixed, all with regression tests)

1. **Queue stranding under a promote-time fault** — a failure after a completion was committed but before the
   next queued call was promoted left the queue permanently blocked. All fault points now run before mutation.
2. **Declaration tampering by attribute swap** — `fns.declared = {...}` replaced the frozen table. Build-time
   attributes are now sealed.
3. **Event flood** — the near-exhaustion warning would have fired on every allocation past 90 %.
4. **Unimportable runtime** — 4.2.0's package `__init__` imported the pk_core-bound component eagerly.
5. The property harness also caught a bug in its *own* reference model (`True == 1` as a call id); the
   minimized sequence is retained in `tests/corpus/` as a regression.

## Disposition

The INV-16-owned runtime is now materially complete as a model: real bridge, canonical ABI transport, bounded
history, finite call ids with generations, configurable re-entrancy, structured cancellation, telemetry that
cannot block lifecycle transitions, and executable race/stress/property/fault/security/rollback evidence.

The bridge's p99 cost does **not** meet the 5 µs contract SLO in this Python model on this host
(`evidence/bench/bridge.json`, gate check `bridge_slo_p99_lt_5us: false`); the SLO must be certified on the
production runtime or revised through governance.

**Production certification remains NO_GO.** The blockers are inputs this archive cannot produce:
`pk_core` (item 1), the real sibling fixtures INV-15/11/10/17/20 (items 2–6), the production compiler backend
and native wait primitive (items 7, 8, 21 on a certified host), and owner decisions — licence terms, residual-risk
sign-off, release key, on-call and waivers (items 27, 36, 40, 42). Each is listed with its unblock path in the
ledger. No item is recorded PASS on the strength of a surrogate or a skipped test.
