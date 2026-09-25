# Changelog - PLN-02

## 4.3.0 - 2026-09-23

Executes `PLN02_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (39 items). Resolver semantics and
revision identity are unchanged for valid inputs; v4.2 callers need no changes.

### Added
- Production control modules: `service`, `errors`, `context`, `versioning`, `admission`, `trust`, `secret_refs`,
  `catalogue`, `policy`, `store`, `audit`, `config`, `oam`, `wit`, `observability` (see README table).
- Public schemas `PK_ERROR/1`, `PK_SIGNED_CATALOGUE/1`, `PK_PLANE_CONFIG/1`.
- `tools/gate.py` (fail-closed release gate, signed evidence), `tools/traceability.py` + `TRACEABILITY.json`
  (39 MC items x 100 checklist requirements, zero orphans), `tools/bench.py` (perf/soak, thresholds).
- 66 new tests: unit/negative per MC, fault/recovery/partition, mock integration with six adjacent layers,
  seeded fuzz/property campaigns with committed corpus, schema conformance.
- Documentation: normative spec, proposed ADR, ownership/escalation/governance, threat model, isolation
  profile, failure catalogue, telemetry governance, runbooks, compatibility matrix, distribution policy.
- Packaging: `pyproject.toml` (reproducible wheel verified), `requirements.lock`, CI matrix workflow.
- Legal placeholders: `LICENSE` (owner decision pending), `NOTICE`, `THIRD_PARTY_NOTICES.md`, `REUSE.toml`.

### Fixed (found by the new fuzz campaign)
- `resolver`: a component or envelope with a non-string key raised `TypeError` instead of the typed
  `INVALID_APPLICATION` refusal (regression `FuzzRegressions.test_r001_non_string_component_key`).
- `oam`: non-list `traits`/`policies` or an unhashable trait `type` raised `TypeError` (regression `test_r002`).

### Not done (honestly reported, gate verdict NO_GO)
- Owner decisions: MASTER.md source (MC-01), ADR approval + named owners (MC-02), governance evidence (MC-38),
  licence (MC-39, left unresolved by owner choice).
- External evidence: deployment isolation (MC-20), CI matrix execution (MC-34), fleet environment (MC-35),
  and the PARTIAL residuals listed in `TRACEABILITY.json`.

## 4.2.0 - 2026-09-22

Repository audit, parser hardening, resolver correctness, contract-schema, and test pass.

### Correctness and integrity

- Moved deterministic resolution logic into standalone `resolver.py` so it can be tested without `pk_core`.
- Fixed a revision-identity collision class: v4.1 hashed component names but not their interface/capability declarations; v4.2 hashes normalized component specifications and uses the full SHA-256 digest.
- Added `verify_revision()` to detect revision mutation after resolution.
- Added a provider-binding digest to resolved revisions.
- Refused unbound required imports and ambiguous imports with multiple producers.
- Added explicit `else`/verification paths in resilience checks so a missing refusal cannot be reported as satisfied.

### Validation and fail-closed behavior

- Added bounded identifier, version, component, edge, capability, interface, provider, and catalogue validation.
- Reserved `:` out of component names so `component:capability` binding keys cannot collide.
- Added duplicate-edge rejection, strict boolean capability requirements, unknown-field rejection, and canonical JSON encoding.
- Added stable machine-readable error codes and detail dictionaries for validation, unsatisfied capability, interface incompatibility, and revision-integrity failures.

### Versioned contracts

- Added `resolve_document()` for `PK_APPLICATION/1` and `PK_PROVIDER_CATALOGUE/1` envelopes.
- Added Draft 2020-12 JSON Schemas for all three public document contracts.
- Added reference application/catalogue fixtures.

### Test hardening

- Added standalone resolver unit tests covering deterministic identity, mutation detection, malformed inputs, duplicate graph elements, missing capabilities, unbound/ambiguous imports, schema version rejection, and non-mutation of caller inputs.
- Added optional JSON Schema validation of fixtures and generated revisions.
- Verified the resolver suite under normal Python and `python -O`.
- `pk_core` conformance tests remain skipped in the supplied standalone archive because `pk_core` is not included; this is recorded as a remaining integration gap rather than treated as a pass.

### Documentation

- Corrected the README claim that `MASTER.md` was present in the supplied archive.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md` with post-hardening findings.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::resolve: an edge naming an unknown component crashed with KeyError -> IncompatibleInterface
- component.py::resolve: duplicate component names silently overwrote each other in by_name -> ValueError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
