# GAP-14 Data-gravity manager - Audit / Fix / Hardening Report

**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Audit date:** 2026-09-22

## Executive result

The component parsed and compiled, but the archive was not self-verifying and several runtime behaviors contradicted its stated production contract. The 4.2.0 pass separates the decision engine from the conformance framework, removes unsafe implicit cost assumptions, strengthens validation and decision evidence, adds standalone tests and schemas, restores the missing master-workflow artifact, and records unresolved estate dependencies explicitly.

## Findings fixed

1. **All shipped tests could skip.** `pk_core` absence caused the complete test class to skip, leaving the ZIP with zero executed behavioral checks. Added standalone engine tests plus package-integrity tests that run without `pk_core`.
2. **Missing `MASTER.md`.** README claimed it existed but the archive did not contain it. Rebuilt it from the authoritative 100-item checklist with generated prompt/workflow scaffolding and clear provenance wording.
3. **Decision logic coupled to `pk_core`.** Importing the package pulled in conformance dependencies. Core logic moved to `engine.py`; component symbols are lazy-loaded.
4. **Missing route cost silently became 1.0.** This could choose a direction on fabricated economics. Cross-site decisions now require an explicit locality multiplier and raise `CostModelError` when absent.
5. **Incomplete numeric validation.** Infinite sizes/multipliers and booleans could pass prior checks. All dataset/cost inputs now require finite, non-negative real values and valid non-empty identifiers.
6. **Mutable configuration after construction.** Caller-owned dict/set mutation could change a live manager. Configuration is now copied and frozen at construction.
7. **No explicit asymmetric egress rate.** Added per-route `egress_per_gb` overrides with a validated default rate.
8. **SLO/response mismatch.** Successful recommendations promised a full cost breakdown but exposed only total costs. Each candidate and selected result now includes a structured cost breakdown.
9. **Weak machine-readable reasoning.** Added stable `reason_code`, `elimination_details`, and coded exceptions while retaining legacy string fields.
10. **Accidental tie-break semantics.** Lexical ordering implicitly favored move-compute. The tie rule is now explicit and documented: keep data resident on exact cost ties.
11. **Illegal co-located state could look healthy.** A no-op recommendation now refuses when the dataset's current site violates residency.
12. **Interface schemas absent.** Added JSON Schema 2020-12 documents for dataset, cost breakdown, and recommendation payloads.
13. **Conformance test accepted unlisted partials by note text.** Removed the broad “not installed” exemption; only explicitly enumerated `KNOWN_PARTIAL` items may pass as partial.

## Compatibility notes

The successful recommendation payload retains `schema`, `direction`, `to`, `cost`, `reason`, `options`, and `eliminated`. New fields are additive. Configuration/input validation is intentionally stricter, and missing cross-site locality data now fails closed instead of defaulting to `1.0`; callers that relied on the implicit fallback must provide route multipliers.

## Verification performed in this audit environment

- Safe ZIP extraction/path traversal check: **PASS**
- Python syntax/bytecode compile: **PASS**
- Standalone engine unit tests: **PASS (11/11)**
- Package integrity tests: **PASS (3/3 always-on checks; 2 `pk_core`-dependent checks skipped because the dependency is external)**
- `pk_core` full 100-check conformance: **NOT EXECUTED** because `pk_core` is not present in this archive/environment

The absence of `pk_core` is therefore recorded as a residual P0 dependency rather than being represented as a production GO result.

## Residual gaps

See `MISSING_COMPONENTS.md`. The highest-priority gaps are authenticated/versioned adapters to GAP-13/GAP-03/GAP-05/SCH-01/PLN-06, tenant/workload identity, decision provenance, tamper-evident audit output, production configuration lifecycle, and full estate integration/gate execution.
