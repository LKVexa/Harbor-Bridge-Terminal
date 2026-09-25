# Changelog - INV-41

## 4.3.0 - 2026-09-22

Execution of the v4.2.0 Missing Component Remediation Checklist. See `REMEDIATION_REPORT.md`.

### Fixed (found by this pass's own tests)

- Identifiers accepted NUL/newline/control characters and unbounded length (REG-001/002; fuzz PR004).
- `Authority`, `Holder` refused pickling/copying only because an internal `mappingproxy` happened to be unpicklable; now explicit.
- Operation elements were hashed before being type-checked, so a hostile `__hash__`/`__eq__` object ran inside `frozenset()`; elements are now type-checked first.
- No bound on operation-set size, policy size, holder size or membrane depth; hard limits added (`LimitExceeded`, INV41-E006).

### Added

- `errors.py` stable error namespace INV41-ERR/1 and outcome model; `audit.py` hash-chained HMAC audit + offline verifier; `config.py` signed, versioned, transactional configuration with rollback and migration; `identity.py` adapter + principal binding; `telemetry.py` metrics/logs/traces; `resilience.py` retry/breaker/admission/fault injection; `broker.py` instrumented facade with health, reasons, explain, lineage, quarantine; `preflight.py`; `isolation.py` process tier + capability bridge.
- Governance (OWNERS, CODEOWNERS, ADR-0001, waivers, blockers), requirements + traceability, interface contracts and golden vectors, threat model, operations, data protection, compatibility matrix.
- Test suites: contracts, properties/model-based fuzzing, races, subsystems, isolation, governance; tools for mutation, benchmark gate, scale/soak/burst/partition, compat, estate gate, deterministic release build, release gate, CI orchestration.


## 4.2.0 - 2026-09-22

Security-model correction, dependency decoupling, and post-update audit.

### Fixed

- Replaced publicly constructible capability references with guarded, sealed reference minting.
- Added explicit `Authority` domains with immutable resource/operation bootstrap policy.
- Added per-authority seals so an impostor authority using the same textual ID cannot inject a reference into a legitimate holder.
- Replaced mutable holder dictionaries with immutable, authority-bound holders.
- Blocked delegation from revoked references.
- Preserved inner membrane revocation through nested wrapping and de-duplicated re-wrapping by the same membrane.
- Replaced inaccurate membrane `issued` counting with weak-reference tracking of still-live descendants, including attenuated/nested references.
- Made capability references intentionally non-serializable and redacted bearer tokens from `repr`.
- Added strict validation for resource names and operation sets.

### Hardened

- Moved security primitives to dependency-free `capabilities.py`; package import and core security tests no longer require `pk_core`.
- Added lazy loading for estate integration objects.
- Added `PK_REFERENCE/1` and `PK_MEMBRANE/1` JSON schemas.
- Added `SECURITY.md` with the explicit same-interpreter trust-boundary limitation.
- Added 19 standalone security tests plus normal/optimized-mode self-checks.
- Preserved `_verify()` rather than bare `assert` for estate behavioural checks.

### Audit result

- Standalone primitives: PASS (16 tests).
- Self-check: PASS under normal Python and `python -O`.
- Python compile: PASS.
- `pk_core` 100-item gate: UNVERIFIED in this archive because `pk_core` is absent; its three integration tests skip rather than execute.
- Remaining production gaps are enumerated in `POST_UPDATE_AUDIT.md` and `POST_UPDATE_AUDIT.json`.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- Replaced bare `assert` in the estate adapter with `_verify()` so behavioural checks survive `python -O`.
- Added explicit failure when expected refusal paths do not occur.
- Added stdlib conformance checks and version pinning.

### Defects fixed

- Fixed nested membrane wrapping so revoking an inner membrane still invalidates an outer-wrapped reference.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
