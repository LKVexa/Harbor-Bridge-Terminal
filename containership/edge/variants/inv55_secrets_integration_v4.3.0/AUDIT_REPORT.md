# INV-55 Repository Audit Report — 4.2.0

## Scope

Original upload SHA-256: `20ec869d9f121e69ceb391692d01822b986c67bc3119aca6e7e65c14dbb2c325`.

Audit target: standalone `inv55_secrets_integration` repository uploaded as version 4.1.0. The pass covered parsing/compilation, secret-redaction behavior, authorization semantics, lease semantics, rotation, failure handling, time handling, resource bounds, concurrency, version consistency, documentation consistency, test behavior under optimized Python, and production-completeness against all 100 `CHECKLIST.json` requirements.

## Baseline findings in 4.1.0

### Critical/High

1. **Secret wrapper was still plaintext-bearing `str`.** Although `repr`, `str`, formatting, and concatenation were overridden, inherited `str` operations exposed plaintext. Confirmed leak paths included slicing, indexing, `encode()`, `lower()`, `upper()`, `replace()`, and `str.join()`.
2. **Lease semantics were overstated.** The prior assessment claimed a copied value becomes useless at lease end. Once plaintext is delivered to application code, this component cannot retroactively erase or invalidate that copy; only provider-enforced credential expiry/revocation can provide that property.
3. **Secret-name existence oracle.** `resolve()` returned `SecretNotFound` for absent names but `SecretDenied` for existing unauthorized names, allowing an unauthorized caller to distinguish existence.

### Medium

4. **Caller-supplied time.** `resolve()`/`use()` accepted arbitrary `now` values, enabling time rewind in the reference model.
5. **Lease context was not bound.** The lease was a mutable dictionary and `use()` did not bind it to broker/application/name context.
6. **No explicit revocation or version retirement enforcement.** Contract failure modes mentioned retirement but the reference behavior did not implement it.
7. **Unstructured string audit log.** Logs were free-form strings rather than typed events.
8. **Log-injection surface.** Application and secret identifiers accepted arbitrary control characters.
9. **Unbounded in-memory audit/input/history.** No caps existed for audit growth, secret size, app-scope size, secret count, or version history.
10. **Unsynchronized mutable state.** Rotation/resolution/revocation state had no lock for concurrent use.
11. **README inconsistency.** It asserted that `MASTER.md` was present even though the file was absent.
12. **Standalone conformance blind spot.** `pk_core` is not in the uploaded repository, so the three existing conformance tests skip and cannot verify the claimed 100-item gate here.

## Changes applied in 4.2.0

- Replaced `Secret(str)` with non-string `_SecretValue` using `__slots__`, redacted diagnostics, and blocked serialization.
- Added immutable `SecretLease` bound to issuer, application, secret name, version, issue/expiry time, and monotonic lease ID.
- Added structured `AuditEvent` records with bounded retention and no value field.
- Added strict identifier validation to prevent control-character log injection and oversized identifiers.
- Made absent and unauthorized resolution failures externally indistinguishable.
- Added broker-owned monotonic time and fail-closed clock rollback/non-finite detection.
- Added TTL validation and bounded reference-model resources (`audit_limit`, secret length, scope size, secret count, version count).
- Added `RLock` serialization around broker state mutation/read-check sequences.
- Added explicit lease revocation and version retirement behavior.
- Preserved append-only rotation: existing leases remain bound to old versions until expiry/revocation/retirement; new resolves receive the latest version.
- Corrected contract/README language about what a lease can and cannot invalidate after plaintext delivery.
- Added focused stdlib tests covering redaction, serialization blocking, authorization, existence-oracle resistance, broker/app/name binding, expiry, revocation, retirement, clock rollback, identifier validation, resource bounds, concurrency, TTL validation, and rotation.
- Version bumped consistently from **4.1.0** to **4.2.0** in `VERSION`, `__init__.py`, tests, README, and changelog.
- Added `MISSING_COMPONENTS.md` with a production-completeness audit and 100-requirement status matrix.

## Verification performed

- `python -m compileall -q inv55_secrets_integration` — **PASS**.
- `python -m unittest discover -s inv55_secrets_integration/tests -v` — focused tests **PASS**; three `pk_core`-dependent tests **SKIPPED** because the dependency is absent.
- `python -O inv55_secrets_integration/tests/test_secrets_primitives.py` — **PASS**.
- Version string consistency check — **PASS** at 4.2.0.
- JSON parse of `CHECKLIST.json` — **PASS**, exactly 100 unique checklist items across ten dimensions.
- Zip path traversal check on the uploaded archive — **PASS** before extraction.

## Verification limitation

The production conformance claim cannot be independently re-certified from this standalone upload because the real `pk_core` package and adjacent estate components are not present. Skipped conformance tests are therefore reported as **not executed**, not as successful. `MISSING_COMPONENTS.md` enumerates the concrete components still absent after hardening.

---

## 4.3.0 addendum - missing-component implementation pass (2026-09-23)

Input: `docs/requirements/missing-component-checklist-v4.2.0.md` (100 components). Output status:
P0 19/9/3, P1 16/15/3, P2 16/15/4 (implemented/partial/open) - see `evidence/traceability.json`.

Defects found and fixed by the new verification during this pass:

1. **Clock rollback escaped the API** - tracing read the rollback-checking clock before the error boundary. Fixed (raw clock for tracing). Found by `test_security_adversarial.FailClosed.test_clock_rollback_denies`.
2. **Malformed input crashed public operations** (`traceparent` of non-string type, non-dict request). Found by seeded fuzzing; fixed.
3. **Unexpected exceptions propagated** - now fail closed as `INV55-E999-INTERNAL`, text not leaked.
4. **Cross-tenant quota exhaustion** - per-tenant buckets were keyed on unauthenticated request fields; now charged after authentication.
5. **Non-durable scope/retire change on persistence failure** - state is now written ahead of the in-memory change.
6. **Per-decision policy digest recomputation** - 2.73x per-tenant overhead; cached, now 0.99x.
7. **Protocol family not bound to operation**, **idempotency key not bound to secret name**, **Vault DR secondary reported reachable** - fixed.

Verification: 124 pass / 6 skip / 0 fail (also under `python -O`); secret scan clean; exit gate `NO_GO`
because the real-Vault and pk_core suites cannot run here and 12 P0 components need external action.
