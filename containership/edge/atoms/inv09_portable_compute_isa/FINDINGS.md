# Findings raised and fixed during the v4.3.0 pass

Every finding has a permanent regression test (checklist items *-034, M14-029, M15-016).

| ID | Found by | Component | Defect | Fix | Regression |
|---|---|---|---|---|---|
| F-01 | fault injection | M09 | A tampered cache entry flipped to `accept` was served and re-attested | per-process HMAC on entries; mismatch → discard + re-validate | `tests/test_faults.py:test_cache_corruption_cannot_admit` |
| F-02 | differential (V8) | M01 | GC value-type bytes (e.g. `0x6c`) classified `MALFORMED` instead of `UNSUPPORTED_PROPOSAL` | `GC_TYPE_BYTES` classification | fuzz seeds 1/3; `oracle_corpus` |
| F-03 | differential (V8) | M01/M02 | typed `ref.null <typeidx>` and table ref-type `0x71` misclassified | proposal classification in decoder + const exprs + body | fuzz seeds 3/5/6 |
| F-04 | unit test | M13 | Deadline was only checked when the step counter crossed a multiple of 4096, so small modules never checked it | `_next_check` scheduling; first step always checks | `test_nondeterministic_failures_not_cached`, `test_deadline_mid_validation` |
| F-05 | unit test | M09/M10 | `cache or ValidationCache()` discarded an injected empty cache (empty cache is falsy) | explicit `is not None` | `test_cache_semantics` |
| F-06 | differential (V8) | M02 | (not a defect) `global.get` of a non-imported global in a constant expression | kept strict: pinned spec is Wasm 2.0 | `oracle_corpus.KNOWN_DIVERGENCE` |
| F-08 | soak | M27 | In-memory audit stream grew without bound (~45 MB growth over a 90 s soak) | bounded in-memory window; durable copy is the file sink; windowed chain verification | `test_audit_memory_window_bounded`, `evidence/soak.json` |
| F-07 | benchmark | M29/M30 | p99 ≈ 2.4 s at 4 MiB vs SLO 20 ms | **open** — ADR-0006 | `evidence/perf_gate.json` |
