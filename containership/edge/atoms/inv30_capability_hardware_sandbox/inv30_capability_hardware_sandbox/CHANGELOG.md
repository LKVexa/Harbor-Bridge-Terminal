# Changelog - INV-30
## 4.3.0 — 2026-09-23 — missing-component remediation (71 gaps)

### Fixed (defects found while integrating against the real pk_core 4.0.0 + siblings)
- Lazy-only package import hid the component from `pk_core.Registry`: `python -m pk_core run INV-30` reported
  "unknown element" in a full estate. Eager import when a supported pk_core is present (regression test added).
- `deps._parse("5.0.0rc1")` read the patch as 1 (digits concatenated) — could have accepted pk_core 5.0.0 pre-releases.
- Decision records leaked raw tenant ids; now hashed tenant buckets.
- Deadline was checked before schema validation, so malformed deadlines surfaced as DEADLINE_EXCEEDED;
  shape validation now precedes auth, admission and state.

### Added
- Service boundary with opaque handles, HMAC auth + replay protection, deny-by-default authz, signed tenant-bound
  root grants, admission control, deadlines, idempotency, revocation sweep, quarantine, emergency disable.
- Backend abstraction; `enforcement` stamped on every success record; `HARDWARE_REQUIRED` refusal; CHERI adapter
  (native helper not built — no CHERI hardware/toolchain available).
- Local CHERI discovery published through GAP-02; environment report.
- 7 JSON Schemas + validator; PK_FAILURE/1 envelope (25 codes); compat + reference fixtures.
- Config system (4 deployment overlays), secret references, tamper-evident audit ledger, metrics/logs/traces/
  decisions, dashboards + alert rules, benchmark harness + thresholds, release evidence + exit gate, operator CLI,
  traceability matrix, CI workflow, pyproject + lock, LICENSE/NOTICE/SECURITY, 20 governance/ops documents.
- Tests: 10 → 99 (property/fuzz, concurrency, contracts, adversarial T-01…T-16, service, resilience/fault
  injection, config/supply chain, ops, framework + sibling integration, hardware conformance [skips ⇒ NO_GO]).

### Changed
- `Capability` equality is identity-based and `repr` hides `base` (no raw authority in diagnostics).
- `check`/`derive`/`invalidate` are linearisable per capability (lock); derivation depth ≤ 64; 64-bit address cap.
- Component reports C031/C068/C084 PARTIAL without CHERI hardware and C009/C010 PARTIAL until signed off, so the
  pk_core gate now says CONDITIONAL_GO instead of an unconditional GO.


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
