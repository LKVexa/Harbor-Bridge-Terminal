# Changelog - GAP-09

## 5.0.0 - 2026-09-22

Security-boundary hardening and production-gap audit. Major version bump because the secure ingestion path no longer treats caller-supplied booleans/attestation strings as production proof.

### Security and correctness

- Added `runtime.py`, independent of optional `pk_core`, with standalone executable tests.
- Added `submit_verified()` and `TrustVerifier`; production ingestion fails closed without an external verifier.
- Added scoped `ReporterAuthority` enforcement for tenant/environment/site/workload authorization.
- Added bounded submission-ID replay detection.
- Equal-timestamp conflicting samples/reporters now fail closed; exact same-reporter duplicates are idempotent.
- Stored values now retain reporter/submission/receive-time provenance and query responses repeat tenant/environment/site/workload attribution.
- Empty batches, non-finite values, invalid identifiers, future timestamps and query-time regressions are refused.
- Whole-batch staging remains atomic; state is guarded by an `RLock`.
- Added global capacity bounds for batch size, signal cardinality, reporter cardinality, rejection history and replay history.
- Added structured error codes and internal runtime counters.
- Corrected pk_core behavioral evidence mappings so runtime checks no longer overwrite unrelated checklist requirements.
- Legacy boolean trust API is disabled by default and available only behind explicit `allow_legacy_trust=True`.

### Interfaces and verification

- Submission interface advanced to `PK_SIGNAL_SUBMISSION/2` with reporter, submission ID, issued-at time, signature and attestation evidence.
- Added JSON Schemas for submission/query/catalogue contracts.
- Advanced the breaking query contract to `PK_SIGNAL_QUERY/2`; retained the legacy `/1` response schema for migration validation.
- Added 31 standalone runtime regression tests; these execute without `pk_core`.
- `pk_core` orchestration tests still skip when the dependency is absent; skipped tests are no longer described as a production pass.
- Added `AUDIT_REPORT.md`, `SECURITY.md`, and `MISSING_COMPONENTS.md`.
- Corrected README claim that `MASTER.md` was present; it was missing from the uploaded archive.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::SignalStore.submit: an unattributed sample mid-batch raised only after earlier samples were stored (state mutated before the refusal) -> validate the whole batch first
- component.py::SignalStore.submit: attestation check was a deny-list (== "untrusted"), so "", None or any unknown level was accepted; signed accepted any truthy value -> require level in {software, hardware} and signed is True
- component.py::SignalStore.submit: future-dated samples (at > now) always won the out-of-order check and read with negative age as fresh, pinning a forged value -> refused with ValueError
- component.py::SignalStore.submit: empty signal name and NaN/non-numeric values accepted -> refused

### Gate

All 100 requirements satisfied under python and python -O. *(Historical 4.1.0 release claim retained from the uploaded package; this v5 audit could not independently reproduce that gate because `pk_core` was not included.)*

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
