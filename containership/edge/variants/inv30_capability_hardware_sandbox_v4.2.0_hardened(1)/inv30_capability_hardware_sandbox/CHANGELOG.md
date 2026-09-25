# Changelog - INV-30

## 4.2.0 - 2026-09-23

Second audit, hardening, and verification pass.

### Fixed and hardened

- Split dependency-free capability semantics into `core.py`; importing and testing the core no longer requires `pk_core`.
- Made package integration imports lazy so a missing framework dependency does not suppress core verification.
- Added strict type validation for bounds, access sizes, validity, operations, and permissions; booleans are no longer silently accepted as integers.
- Normalized permission inputs defensively and reject string/bytes pseudo-collections and non-string permission members.
- Added stable machine-readable refusal codes via `CapabilityError.as_dict()`.
- Added standalone boundary, attenuation, invalidation, mutation, malformed-input, and error-code tests.
- Removed the README claim that `MASTER.md` is present; it is not included in this archive.

### Verification limitation

- `pk_core` is not bundled with this repository, so framework-level 100-item conformance remains externally dependent and cannot be independently executed from this archive alone.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Capability.check: size <= 0 was accepted, so check(address=limit, size=-1) was permitted for an address outside the bounds -> non-positive size raises BoundsViolation
- component.py::Capability: base/length/permissions/valid were plain mutable attributes, so cap.length = 2**64 amplified and cap.valid = True resurrected an invalidated capability (breaks "invalidation is permanent") -> __setattr__ guard: bounds/permissions immutable after init (Amplification), valid can only go True->False (Invalidated); assess_resilience now also exercises the resurrection refusal
- component.py::Capability.__post_init__: a caller's mutable set was stored as permissions (permissions.add("write") amplified), str permissions were split into characters, negative base accepted -> normalise to frozenset, TypeError for str, ValueError for negative base
- component.py::Capability.derive: negative length surfaced as a ValueError from the constructor instead of a named refusal -> Amplification

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
