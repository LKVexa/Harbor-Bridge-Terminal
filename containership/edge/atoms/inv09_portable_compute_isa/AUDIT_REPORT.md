# INV-09 Portable Compute ISA — Audit Report

**Audited version:** 4.1.0  
**Hardened version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** package structure, validator policy logic, contract alignment, testability, input hardening, failure behaviour, version consistency, and production-readiness gaps.

## Executive result

The package is structurally small and readable, but v4.1.0 was not a production Wasm validator. Its `validate()` function accepted a caller-populated `Module` descriptor and therefore trusted `used_features`, `sections`, `size_bytes`, and `well_formed` facts rather than deriving them from raw module bytes. That remains the largest architectural gap and is intentionally not hidden by the v4.2.0 hardening pass.

v4.2.0 hardens the descriptor-level policy kernel, fixes a fail-open contract mismatch, makes the critical validator independently testable without `pk_core`, and adds explicit production-gap documentation.

## Findings and remediation

| ID | Severity | v4.1.0 finding | v4.2.0 disposition |
|---|---|---|---|
| A-01 | Critical | No raw Wasm binary decoder/type validator; security facts are caller supplied. | **Open / explicitly scoped.** Tracked as missing component M-01. Policy kernel documentation now forbids sourcing these facts from untrusted headers/manifests. |
| A-02 | High | Declared capability outside the selected profile could return `valid=True` when unused. | **Fixed.** `FeatureRefused` is raised for declared or used features outside the profile. |
| A-03 | High | Unknown declared features could be accepted when unused. | **Fixed.** Feature registry is fail-closed; unknown/unregistered features raise `ValidationFailed`. |
| A-04 | Medium | Non-hashable `profile` values could fail with implementation `TypeError` rather than the API's validation error path. | **Fixed.** Profile type is checked before lookup. |
| A-05 | Medium | `well_formed` accepted arbitrary truthy/falsy values, weakening descriptor integrity. | **Fixed.** Requires an actual `bool`. |
| A-06 | Medium | Feature-set elements were not type/syntax checked. Mixed types could break sorting/error paths or create ambiguous feature identifiers. | **Fixed.** Feature names are bounded strings matching a conservative slug grammar. |
| A-07 | Medium | Mutable `set` inputs were evaluated directly despite the frozen dataclass annotation. | **Hardened.** Sets are snapshotted to `frozenset` before policy evaluation. |
| A-08 | Medium | No bound on feature-count or module-name diagnostic input. | **Fixed.** Added explicit metadata bounds and control-character rejection. |
| A-09 | High | All existing tests were skipped when `pk_core` was unavailable, leaving the validator entirely untested in a partial checkout. | **Fixed for validator kernel.** New standalone tests run without `pk_core`; full 100-item conformance remains dependency-gated. |
| A-10 | Medium | Documentation implied byte-level validation more strongly than the implementation delivered. | **Fixed.** README and validator docstrings now state the descriptor-level boundary and production prerequisite. |
| A-11 | Medium | No machine-readable failure taxonomy beyond Python exception classes. | **Open.** Coarse exception `code` attributes added; full structured failure contract remains missing. |
| A-12 | High | No fuzzing, malformed-Wasm corpus, differential validator testing, or cross-runtime certification assets. | **Open.** Tracked in `MISSING_COMPONENTS.md`. |
| A-13 | High | No cryptographic artifact identity/provenance binding between validation result and exact module bytes/profile version. | **Open.** Tracked as missing production capability. |
| A-14 | Medium | No benchmark proves the stated p99 <20 ms for modules up to 4 MiB. | **Open.** Benchmark harness and release threshold are missing. |
| A-15 | Medium | `pk_core` dependency and supported version are not declared in a package manifest in this component. | **Open.** Packaging/dependency pinning is missing. |

## Verification performed in this package

The hardened package is checked with Python bytecode compilation, JSON parsing of the 100-item checklist, standalone unit tests for `validator.py`, optimized-mode (`python -O`) standalone tests, archive integrity testing, and version-reference consistency checks.

The external `pk_core` conformance suite is still conditional on the wider project harness. A skipped suite is **not** treated as evidence that all 100 requirements pass; production certification requires the harness and objective evidence for the remaining requirements.

## Compatibility note

v4.2.0 intentionally tightens validation. A descriptor that declares a capability outside the selected profile, even if it does not use that capability, now fails closed. Callers relying on v4.1.0's permissive behaviour must either select an appropriate profile or stop declaring the disallowed capability.

## v4.3.0 disposition of open findings

| ID | v4.3.0 disposition |
|---|---|
| A-01 | **Fixed.** `prod/decoder.py` + `prod/typecheck.py` decode and type-check raw bytes; facts are byte-derived only (ADR-0001). 0 false accepts vs V8 over the fuzz campaign. |
| A-11 | **Fixed.** `PK_VALIDATION_FAILURE/1` structured failures with byte offsets (M12). |
| A-12 | **Partially fixed.** Structure-aware fuzzer + V8 differential; second reference and cross-runtime certification still open. |
| A-13 | **Fixed.** SHA-256 identity + Ed25519 attestations binding digest, profile, bundle, engine, limits (M07/M08). |
| A-14 | **Measured - fails.** p99 ≈ 2.4 s at 4 MiB vs 20 ms SLO (ADR-0006). |
| A-15 | **Partially fixed.** `pyproject.toml` + `requirements.lock` (hashes to be generated in CI). |
