# GAP-01 Edge Node Supervisor — v4.2.0 Audit Report

**Audit date:** 2026-09-22  
**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Scope:** package integrity, Python runtime behavior, lifecycle safety, drain semantics, health evidence, dependency isolation, testability, and documented production gaps.

## Executive result

v4.1.0 contained a useful lifecycle/drain reference implementation but was not independently testable because package import required an external `pk_core` installation. It also contained several fail-open or ambiguous edge cases: future-dated health evidence could be treated as fresh, timestamps could regress, duplicate workload IDs silently overwrote existing entries, initial state and persisted dictionaries were not validated, and repeated deadline polling could duplicate breach records.

v4.2.0 extracts the node runtime into a dependency-free module, makes `pk_core` integration optional at import time, validates state and time inputs, rejects duplicate workload identities, treats future-dated health as invalid, rejects clock regression, makes breach recording idempotent for identical polls, and adds standalone behavioral regression tests.

## Findings and applied fixes

1. **Hard package dependency on `pk_core` — fixed.** Importing `gap01_edge_node_supervisor` failed before tests could skip unavailable integration checks. Runtime logic now lives in `supervisor.py`; package import remains functional without `pk_core`.
2. **README inventory mismatch — fixed.** README claimed `MASTER.md` was present, but it was absent from the ZIP. The false claim was removed and the actual package layout is documented.
3. **Future health timestamps accepted as fresh — fixed.** `healthy_at()` now requires `0 <= now - seen <= HEALTH_STALENESS_BOUND`.
4. **Clock regression accepted — fixed.** Health and drain operations reject timestamps older than the supervisor's observed clock.
5. **Invalid initial state accepted — fixed.** `__post_init__()` validates lifecycle state, node name, workload identities/classes, health names/timestamps, and clock.
6. **Duplicate workload IDs silently replaced records — fixed.** `admit()` now rejects duplicate workload identity.
7. **Weak input typing — hardened.** Tick values must be non-negative integers; booleans are rejected as ticks.
8. **Repeated breach polling duplicated evidence — hardened.** Identical deadline breaches at the same observed tick are not appended repeatedly.
9. **Drain response lacked timing context — hardened.** Results now include `deadline` and `observed_at` fields while retaining schema `PK_DRAIN/1`.
10. **No dependency-free regression tests — fixed.** Added `tests/test_supervisor.py` covering health gating, time monotonicity, duplicate admission, cordon behavior, trust-ordered drain, idempotent breach recording, stop-with-residents protection, and terminal stopped state.

## Items deliberately not fabricated

The archive does not contain the wider `pk_core` framework, runtime launch adapters, schemas, persistence layer, control-plane transport, authentication/authorization machinery, or node bootstrap/resource-discovery implementation. v4.2.0 therefore does **not** claim full production certification or that all 100 checklist requirements are independently proven by this ZIP. See `MISSING_COMPONENTS.md`.

## Compatibility notes

- Existing lifecycle state names and legal transitions are retained.
- Existing trust classes and trust-ordered drain behavior are retained.
- `PK_DRAIN/1` output retains its existing keys and adds `deadline` and `observed_at`.
- Callers that previously relied on duplicate workload IDs overwriting state, regressing timestamps, or future timestamps counting as healthy will now receive explicit errors or unhealthy results.

## Verification target

The package must pass Python compilation and the standalone `unittest` suite without `pk_core`. Full 100-check conformance remains an integration verification and requires the external framework and its schemas/evidence tooling.

---

# v5.0.0 Overhaul Addendum (2026-09-22)

**Input:** 4.2.0 · **Output:** 5.0.0 · **Driver:** GAP-01 Professional Missing-Components Checklist v1.0.0 (70 × 30 = 2,100 checks + 20 exit items).

## Result

Most of the missing components named in v4.2.0 are now implemented, tested, or documented. The ones that aren't are listed in `EXCEPTIONS.md` with severity and a target release. Item-level status is in `CHECKLIST_STATUS.md` and requirement-level status in `TRACEABILITY.md`. The exit gate (`tools/exit_gate.py`) currently returns **NO_GO**. It stays NO_GO until someone closes these blocker exceptions: owners and sign-offs (EXC-001), the real Wasm/microVM/unikernel adapters (EXC-004), a license choice (EXC-011) and an independent security review (EXC-012). This is the correct verdict: the gate is working as designed.

## Verification performed in this pass

- Every test suite passes. That includes the property test run at 300 seeds and a SIGKILL-and-recover test that boots the real entry point.
- The stdlib tracer measures about 90% line coverage over 14 runtime modules.
- ruff and mypy both report clean.
- The benchmarks pass the perf gate. A 20-node soak churn run found 0 invariant violations.
- The two defects listed in CHANGELOG 5.0.0 were found by these new tests and fixed.

## Not claimed

This pass does not claim pk_core 100-check conformance, because pk_core was unavailable. It also doesn't claim results on aarch64 or on other Python versions, a verified systemd sandbox on a real host, TPM attestation, or live control-plane interoperability. Each of these has an entry in `EXCEPTIONS.md`.
