# Changelog - GAP-15

## 4.3.0 - 2026-09-22

Execution of the *GAP-15 v4.2.0 Missing Components — Professional Engineering Checklist v1.0.0*
(51 components, 1,040 controls) against this package, delivered as an additive stdlib-only
production layer. `component.py`, `contract.py`, `CHECKLIST.json`, `AUDIT_REPORT.md` and
`MISSING_COMPONENTS.md` are byte-identical to v4.2.0.

### Added — `production/` (20 modules, Python stdlib only)

- `store.py` — SQLite WAL/FULL durable store; append-only ledger and audit tables enforced by
  triggers and SHA-256 chains; CAS revisions; atomic ledger+matrix+revision+audit commits; forward-only
  migrations with downgrade refusal; crash recovery by replay; signed checkpoints; JSONL export;
  signed backups and verified restore-to-staging; bounded retry with backoff+jitter.
- `state.py` — pure event→state→verdict engine used identically for live decisions, historical
  reconstruction, explain and post-restore checks; lifecycle graph; negative-evidence ageing;
  revocation/quarantine/conflict precedence.
- `ed25519.py` + `signing.py` — RFC 8032 Ed25519 (strict S), domain-separated canonical signing,
  versioned scoped trust store with rotation windows and compromise, development key provider that
  refuses production.
- `provenance.py`, `attestation.py`, `timepolicy.py`, `authn.py`, `authz.py`, `schemas.py`, `canonical.py`,
  `partition.py`, `capability.py`, `versions.py`, `negotiation.py`, `features.py`, `policy.py`,
  `scheduler.py`, `offline.py`, `observability.py`, `capacity.py`, `service.py`, `http_api.py`,
  `release.py`, `config.py`, `ops.py`, `fixtures_matrix.py`, `cli.py`, `serve.py`.
- `docs/` ADR-001..009, per-component THREAT_MODEL, RUNBOOKS with anchored failure trees,
  OPERATIONS_CONTRACT, OWNERS.json (unassigned); `deploy/` Dockerfile, systemd unit, example config,
  supported-versions manifest; published JSON Schemas under `schemas/`; alert/dashboard pack under `ops/`.
- `tools/run_checklist.py` — executes the checklist and writes `evidence/`.

### Result (this build environment, CPython 3.11.15)

- Tests: 215 run, 207 passed, 0 failed, 8 skipped
  (the 8 skips are the v4.2.0 pk_core conformance suite; pk_core is still not bundled).
- Controls: 541 LOCALLY_VERIFIED, 121 ARTIFACT_PRESENT_UNREVIEWED,
  33 PARTIAL, 294 BLOCKED, 38 NOT_APPLICABLE,
  13 NOT_IMPLEMENTED, 0 FAILED.
- Exit gate: **NO_GO** (security, DR, review and approval evidence do not exist; every xx-17 and
  EXIT row needs an independent reviewer and named owners).
- Benchmark (single process): certify p99 5.28 ms, ingest p99 22.624 ms.

### Defects found by this pass's own tests and fixed

See `evidence/DEFECTS.log` (5 defects: chain verifier crash on storage-class tamper; separation-of-duties
approvals always denied; exact retries rejected by nonce consumption; unauthenticated callers got
validation detail; single-use token reused inside conflict/bulk workflows).

### Changed

- `__init__.py`: the pk_core-bound symbols are imported only when pk_core is importable, so the
  stdlib production layer loads without it (`PK_CORE_AVAILABLE` flag). `VERSION` 4.3.0.

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening, and version-bump pass.

### Correctness fixes

- `CompatibilityMatrix.certify`: future-dated evidence is now rejected before either compatible **or incompatible** evidence is trusted. v4.1.0 checked clock skew only after the incompatible branch, so a future-dated negative result could be accepted.
- `CompatibilityMatrix.certify`: validates `Triple` and `now`; booleans, negative timestamps, malformed stored records, and invalid lifecycle state now fail closed.
- `Triple`: rejects edge whitespace, control characters, non-strings, empty identifiers, and overlong identifiers.
- `CompatibilityMatrix.coverage`: computes coverage over unique triples and validates input types, preventing duplicate request entries from skewing the metric.
- `contract.py`: certification telemetry now explicitly includes the `end-of-life` verdict.

### Integrity hardening

- Added monotonic `revision` tracking for accepted matrix/lifecycle mutations.
- Added stale-evidence rollback protection: older test results cannot replace newer results.
- Added same-timestamp conflict protection: contradictory results at an identical timestamp are rejected; exact replay is idempotent.
- Added lifecycle transition guardrails: regressions such as `end-of-life -> supported` require explicit `allow_reactivation=True`.
- Caller-supplied initial `results` and `lifecycle` mappings are copied and validated during construction.
- Added deterministic, versioned `matrix_view()` (`PK_COMPATIBILITY_MATRIX/1`) and `lifecycle_view()` (`PK_RUNTIME_LIFECYCLE/1`) exports.
- Certification output now carries environment, matrix revision, typed coordinates, and positive-certificate expiry metadata while preserving the v4.1 string `triple` field.
- Renamed the TTL constant to `CERTIFICATION_TTL_SECONDS` and retained `CERTIFICATION_TTL` as a compatibility alias.

### Verification and documentation

- Expanded stdlib conformance tests for clock skew, replay/conflict handling, lifecycle regression, deterministic exports, invalid input, version pinning, and optimized-mode behavior.
- Corrected the README claim that `MASTER.md` was bundled; it was absent from the supplied archive.
- Added `AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`, and a deterministic `MANIFEST.sha256` integrity manifest.
- Static AST/bytecode compilation and isolated domain-logic smoke tests pass. Full `pk_core` conformance could not be executed in the audit environment because `pk_core` is not bundled/importable here.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::CompatibilityMatrix.certify: END_OF_LIFE verdict returned "triple" as a dict (vars()) while every other verdict returns str -> use str(triple) consistently
- component.py::CompatibilityMatrix.certify: a result timestamped after `now` (clock skew/forged) yielded negative age and stayed CERTIFIED indefinitely past the TTL -> future-dated results are reported UNTESTED and not deployable
- component.py::CompatibilityMatrix.record: accepted non-Triple keys, truthy non-bool `compatible` and negative/non-int times -> TypeError/ValueError
- component.py::Triple: empty artifact/runtime/profile accepted -> validate in __post_init__

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
