# Changelog - INV-29

## 4.3.0 - 2026-09-23

Missing-components implementation pass: the 103-item *INV-29 v4.2.0 Missing Components Implementation Checklist* applied to the 4.2.0 hardened candidate (junkyard chop-shop). Per-item status, evidence and blockers: `MISSING_COMPONENTS_STATUS.json`; requirement traceability: `conformance/TRACEABILITY.json`; gate: `conformance/PK_GATE_RESULTS.json`.

### Added - code (all stdlib-only)
- `admission.py`: identity-bound, attested, replay-protected admission. Tenant allow-list, sha256 module/host digest binding, HMAC-verified `sealed` / `hardened` / optional `measured-boot` attestations (subject-bound, fresh, revocable), dangerous-capability denylist on imports *and* host exposure, per-workload cardinality, capability provenance, nonce + TTL replay guard (bounded, fails closed when full), signed composition records, `verify_record()` for consumers, emergency disable, monotonic policy generations with explicit audited rollback, stable `INV29-E-*` error codes.
- `interfaces.py`: typed capability/interface definitions and a local link check (identical/additive/breaking) enforced in addition to name closure.
- `records.py`: canonical JSON, strict bounded parser (size, depth, duplicate keys, NaN), dependency-free JSON-Schema validator, redaction.
- `schemas/`: machine-readable JSON Schemas for `PK_HYBRID_COMPOSITION/1` and `PK_HYBRID_VERIFICATION/1`.
- `deps.py`: dependency manifest, pk_core startup compatibility assertion, adapters with timeout / bounded retry / circuit breaker, dependency states, labelled test doubles for INV-27 / INV-44 / PLN-04.
- `lifecycle.py`: integrity-checked atomic store, idempotent submit, state machine, reconciliation, revocation, backup/restore, fail-closed operator control file.
- `telemetry.py` + `service.py`: metrics (cardinality-capped), structured redacted logs, W3C trace context, decision-reason stream, explain view, `/healthz /readyz /version /dependencies /metrics /decisions /explain`, alert rules.
- `evidence.py`: hash-chained evidence ledger, waiver register validation, machine-derived gate (P0 un-waivable; stale manifest, failed tests or certification-critical skips block).
- `tools/`: `run_tests.py`, `bench.py` (baseline + perf regression gate), `fuzz.py`, `secret_scan.py`, `build_release.py` (lock, SBOM, checksums, provenance, scans, manifest, traceability, gate), `inv29ctl.py` (disable/enable/backup/restore/rollback/verify-ledger).

### Added - tests (13 new suites)
admission, interfaces, records (contract), lifecycle (incl. disaster recovery), deps (chaos, partition/reconnect, pk_core negatives), properties, fuzz, concurrency, telemetry, service, evidence (gate negatives), soak/burst, supply chain. All pass normally and under `python -O`.

### Added - documents
`docs/` architecture + data flow, threat model, schema evolution, persistence, capacity, compatibility matrix, observability; `governance/` SLO, rollout, security policy, runbooks + incident response, review, waiver register; `OWNERS.md`, `CODEOWNERS`, `RELEASE_CHECKLIST.md`, `NOTICE`, `pyproject.toml`, CI workflow, dashboard.

### Fixed
- `ReplayGuard` defined `__len__`, so an *empty* guard passed as `replay=` was falsy and silently replaced by a default-capacity guard; now compared against `None`.
- `Metrics.inc/set/observe` took `name` as a normal parameter, so a metric label called `name` crashed; parameters are now positional-only.
- `__init__` imported `pk_core` eagerly, making the dependency-free core unimportable without it; the component/contract are now lazy behind the compatibility assertion.
- Adversarial review (two rounds, independent reviewer) found and 4.3.0 fixes, each with a regression test in `tests/test_regressions_review.py`:
  - **critical** - a `frozenset` subclass overriding `__sub__`/`__and__` bypassed import closure and the denylist; a `str` subclass overriding `__eq__` let a valid attestation be reused for another digest. Model and admission inputs now require exact built-in types (subclasses of `WasmModule`/`HostImage`/`str`/`frozenset` refused).
  - **high** - `re.match(...$)` accepted a trailing newline in digests/tenant/nonce; now `fullmatch`, and the schema validator applies ECMA `$` semantics.
  - `verify_record` accepted any key in the keyring and future-issued records; it now requires `expected_key_id` and checks `issued_at` and the validity window.
  - Decision events never reached the structured log (duplicate `event` kwarg swallowed by the fail-safe hook).
  - `Store.restore` could resurrect a revoked composition; terminal states are now never downgraded, and backups are parsed with the strict parser.
  - `derive_gate` returned GO when zero tests ran; `passed > 0` is now required.
  - Ledger truncation was undetectable; `verify()` takes an anchor (head / entry count) recorded in the gate artifact.
  - An empty or malformed control file enabled the tier; it now fails closed.
  - Malformed attestation fields raise `AttestationInvalid` instead of `TypeError`.
- `component.assess_interfaces` without INV-11 now exercises the local typed check (finding stays PARTIAL; INV-11 remains the authority).

### Gate
Machine-derived verdict for this source digest: **NO_GO** - P0 items remain blocked on external components (pk_core, INV-11/27/44, PLN-04, labs) and owner actions. This is the correct result, not a defect.

## 4.2.0 - 2026-09-23

Second audit, correctness hardening, and interface-completeness pass.

### Fixed and hardened

- Added the contract-advertised `verify()` API (`PK_HYBRID_VERIFICATION/1`) with independent unikernel, Wasm, and import-closure results.
- Moved security-critical composition logic into dependency-free `model.py`, so it is testable even when `pk_core` is absent.
- Enforced exact input types for layer count and booleans; Python booleans can no longer pass as integer layer counts.
- Enforced non-empty names and immutable `frozenset[str]` capability sets, preventing malformed or mixed-type capability collections from reaching set/sort operations.
- Validate both Wasm target architecture and host CPU architecture against explicit supported sets.
- Preserve the complete verification record inside successful composition evidence.
- Added standalone negative-path tests covering layer loss, import closure, unsupported architectures, malformed capabilities, invalid names, and environmental layer-count escalation.
- Corrected README claim that `MASTER.md` was included when it is absent from the supplied archive.

### Validation

- Standalone model tests pass under normal and optimized (`python -O`) execution.
- `pk_core` conformance remains conditional on the external `pk_core` dependency.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::compose: required_layers was caller-controlled, so required_layers=1 (or 0) composed a module on an unsealed host / an unhardened module, contradicting "refuse where either layer is absent" -> reject required_layers < 2 and refuse whenever any layer failed
- component.py::compose: WasmModule.architecture was accepted but never checked, so a non-wasm payload counted as the wasm layer -> the wasm layer requires architecture wasm32/wasm64
- component.py::compose: non-set imports/exposes crashed with an opaque TypeError on set difference -> explicit TypeError up front
- component.py::assess_interfaces (items[0]): text claimed the layers are linked on typed interfaces and cited compose, which only matches names -> reworded to state compose matches by name and the INV-11 check (exercised) covers signature drift; status unchanged

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
