# Changelog - INV-25

## 4.3.0 - 2026-09-23

Execution of `INV25_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md`.

### Added
- `errors.py`: stable `PK_DEVICE_ERROR/1` codes (25), redacting serializer; every model rejection now carries a code.
- Resource ceilings (64 devices, 256 registers/device, 4096 aggregate, 1 MiB payload, pre-scan bounds, 32 pending, rate limits).
- `catalogue_from_export()`: strict parser (exact keys, duplicates, NaN/Infinity, depth, size) and `DeviceCatalogue.digest()` over canonical JSON.
- `authz.py`: signed-token verification (issuer/audience/key/revocation/validity/anti-replay, clock fail-closed) and 10 deny-by-default capabilities with break-glass.
- `audit.py`: hash-chained `PK_DEVICE_AUDIT_EVENT/1` log with append-only file sink and chain verification.
- `store.py`: transactional control plane - immutable candidates, separation of duties, CAS activation, atomic durable commit, activation records, rollback to known-good digests, emergency disable/restore, health/readiness, metrics, explain view, fault hooks.
- `provenance.py`, `compat.py`, `pk_bootstrap.py`, `schemavalidate.py`.
- Schemas: error, audit event, config activation, evidence record.
- Tests: 81 new (87 total; 3 pk_core-dependent remain skipped here). Fuzz corpus, contract fixtures for INV-24/35/26/GAP-13/INV-43, benchmark + thresholds.
- Governance: RTM (100 rows), waiver/review/approval registers, ADR-0001, CODEOWNERS, SECURITY.md, SUPPORT.md, 17 docs.
- Tooling: `tools/rtm.py`, `tools/gate.py` (evidence chain + gate + verify), `tools/release.py` (reproducible archive, manifest, CycloneDX SBOM); CI workflow; `pyproject.toml`.

### Changed
- Package import no longer requires `pk_core`; `COMPONENT`/`build_contract` resolve lazily with a machine-readable error.
- Environment names must match the device-name grammar; control/invisible Unicode and case-variant duplicate registers are rejected.
- `DeviceRejected` is now also an `Inv25Error` (still a `PermissionError`).

### Fixed
- In-memory/durable divergence risk: commit point is the atomic file replace; failures after audit emission are recorded as `config.activation_failed`.


## 4.2.0 - 2026-09-23

Audit, remediation, hardening, and verification pass.

### Hardening and fixes

- Extracted the security-critical device model into dependency-free `model.py`, allowing meaningful standalone tests when `pk_core` is unavailable.
- Added strict validation for catalogue environment, device name/class/version, register identifiers, rationale, and reviewer metadata. Unknown classes continue to fail closed.
- Added explicit `DeviceCatalogue.replace()` semantics: a changed device cannot reuse its version, replacement is impossible for unknown devices, and every accepted replacement returns the mandatory surface diff.
- Added deterministic `DeviceCatalogue.export()` output for the `PK_DEVICE_CATALOGUE/1` interface.
- Added JSON Schema documents for both public data contracts.
- Added six dependency-free unit tests covering registration, malformed input, deny/allow behavior, explicit replacement, version-change enforcement, and cross-device diff rejection.
- Corrected README packaging claims: `MASTER.md` is not present in this standalone archive.
- Public package exports now include the device model classes.

### Verification

- Standalone model tests pass under the local Python runtime.
- Source compiles successfully.
- `pk_core` integration conformance remains unavailable in this standalone archive and therefore cannot be claimed as executed; see `AUDIT_REPORT.md`.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::DeviceCatalogue.register: denylist-only class check admitted any unrecognised class (e.g. "Host-Passthrough", "emulated-ide") -> added PERMITTED_CLASSES allowlist, unknown classes raise DeviceRejected
- component.py::DeviceCatalogue.register: re-registering a name silently overwrote the entry, widening surface with no diff reported -> refuse a changed entry for an existing name
- component.py::DeviceCatalogue.register: empty name and non-frozenset registers (a str counted characters as registers) accepted -> DeviceRejected

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
