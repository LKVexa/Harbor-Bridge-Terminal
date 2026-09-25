# Changelog - INV-03

## 4.3.0 - 2026-09-22

Application of the Professional Engineering Checklist 1.0.0 (70 components) through the chop shop.

### Added
- `hardening/` stdlib-only runtime: 16-control PodSpec evaluator (`PK_HARDEN_EVAL/2`), signed baselines
  (`PK_HARDEN_BASELINE/2`) with epoch-CAS activation/rollback and tighten-only overlays, migration from
  `PK_HARDEN_BASELINE/1`, exception authority on a hash-chained sealed audit ledger, trusted clock,
  authentication/authorization, admission webhook adapter, runtime inventory, drift/quarantine/emergency
  deny-all, verdict hooks (scan, provenance, attestation, IDS), staged rollout, metrics/logs/traces/explain.
- JSON Schemas, fixture corpus, 72 new tests, mutation falsifier, release gate, review tool, CI workflow,
  `pyproject.toml`, SBOM, third-party notice, operations and governance documents.
- `CHECKLIST_STATUS.json` and `RELEASE_GATE.json`.

### Changed
- `__init__.py` imports cleanly without `pk_core` and reports `PK_CORE_AVAILABLE`/`PK_CORE_ERROR`;
  element identity moved to `contract_ids.py` so it no longer needs the framework.

### Fixed during the pass (found by the pass's own checks)
- The admission adapter raised on a non-object `metadata` (found by mypy) — now fails closed.
- A post-validation `assert` in the engine would vanish under `python -O` — replaced by an explicit check.
- Mutation probe survivors: no test proved an allowlisted path still refuses a runtime socket, and no test
  proved a correctly sealed record spliced from a forked ledger breaks the chain — both tests added; 10/10 killed.

### Unchanged
- `policy.py` (4.2.0 evaluator, legacy baseline) and its tests; `component.py`, `contract.py` behaviour.

### Not done (see `CHECKLIST_STATUS.json`)
- 0/70 components complete; gate NO_GO. Blocked on a cluster, `pk_core`, a KMS, a runtime matrix,
  a named owner, ADR approval and the missing `MASTER.md`.

## 4.2.0 - 2026-09-22

Security-focused audit, parsing, repair, hardening, and version-bump pass.

### Fixed

- Fail-open omission: `privileged` must now be explicitly `False`; a missing field no longer passes `not-privileged`.
- Malformed capabilities: `drop`/`add` must be lists of strings; strings or malformed mappings no longer satisfy the control.
- Hostile top-level inputs: malformed workload/spec/exception/time inputs now return a fail-closed decision instead of raising from the policy boundary.
- Timestamp ambiguity: booleans no longer count as integer exception expiries.
- Revocation ambiguity: any non-false/non-null revocation value prevents an exception from being honored.
- Wire compatibility: exceptions now support JSON-safe nested, composite-key, and list forms in addition to the legacy tuple-keyed map.
- Mutable control registry: the published control table is now immutable.
- Documentation drift: removed the incorrect claim that `MASTER.md` is present and documented the actual production-readiness boundary.

### Added

- `policy.py`, a dependency-free security policy module with self-describing evaluation/baseline schemas.
- Dependency-free unit tests that run in normal and `python -O` modes.
- `AUDIT_REPORT.md` with the completed audit and verification record.
- `MISSING_COMPONENTS.md` with prioritized unimplemented production components.
- `RELEASE_MANIFEST.json` and `SHA256SUMS.txt` for artifact inventory/integrity checking.

### Verification

- Python bytecode compilation: PASS.
- Dependency-free policy suite: PASS in normal mode.
- Dependency-free policy suite: PASS under `python -O`.
- `CHECKLIST.json`: PASS, 100 unique ordered items.
- Framework conformance: SKIPPED in this isolated archive because `pk_core` is not bundled/installed; this is recorded as an integration gap, not a pass.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::CONTROLS["non-root"]: `user: 0` (int), "00" or "" passed the non-root control because only the strings "root"/"0" were rejected -> normalise and reject any uid-0 spelling or empty user
- component.py::CONTROLS["drop-all-capabilities"]: drop ALL plus `add: [SYS_ADMIN]` passed; a non-dict `capabilities` crashed with AttributeError -> require no added capabilities, tolerate malformed specs (control fails)
- component.py::evaluate: an exception record without "expires" raised KeyError; a whitespace-only reason counted as recorded -> require int expiry and non-blank reason

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
