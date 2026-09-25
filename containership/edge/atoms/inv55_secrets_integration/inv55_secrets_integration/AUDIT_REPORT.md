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

## 4.3.0 pass: executing the comprehensive missing-component checklist (2026-09-22)

Input checklist sha256 `2dc736412cc80e5cc002e99b4f1f6f78e0f0854db6f51965e6c09cefa18875d2`, candidate zip sha256 `46e810f129a2111a93c6871459cc12783532acba46174e647a550cc3231d9bf9`. The pass was run through the junkyard chop shop. Donor consulted for patterns only: `amplifier-bundle-redaction`. No third-party code was copied.

Result: 49 IMPLEMENTED / 27 PARTIAL / 15 DRAFTED / 9 BLOCKED, 0 complete, gate **NO_GO** (10 PASS, 3 FAIL, 3 BLOCKED). The detail is in `EXECUTION_REPORT.md` and `evidence/PK_GATE_RESULTS.json`.

Verification: `tools/ci.sh` passes on CPython 3.11.15/Linux. It covers compile, secret scan (0 findings), SBOM (0 third-party imports), status registry (0 problems), 110 tests (0 failures, 3 pk_core skips, which the gate counts against itself), the 4.2.0 primitives under `python -O`, and the gate itself. A wheel built with setuptools 79 installs into a clean venv and finds its schemas. Debian's system setuptools 68.1.2 fails with `install_layout`, which is an environment issue.

Not verified, and not claimed: real Vault, real IdP/INV-59, pk_core, hosted CI, other interpreters, the certified performance environment, staging runbook drills, and any human approval.
