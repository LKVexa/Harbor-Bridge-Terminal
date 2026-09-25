# Changelog — GAP-02

## 4.3.0 — 2026-09-22

Execution of `GAP02_v4.2.0_55_Missing_Components_Professional_Checklist.md`.

### Added
- `production/` subpackage (stdlib-only) implementing GAP02-MC-01..40 — see README table.
- Single promotion gate `evidence.promote()`; proof vs observation evidence kinds.
- `Host` access seam: bounded reads, absolute-path/no-shell commands, deadlines; the same probes run on real hosts and fixtures.
- Operations artefacts: `ops/alerts.json`, `ops/dashboard.json`, `RUNBOOKS.md` (one anchor per error code), `COMPATIBILITY_MATRIX.json`, `conformance/cases.json`, `fixtures/lab_manifest.json`, ADR-0001, draft support policy, `PK_CORE_CONTRACT.json`.
- Tools: evidence runner (per-component bundles + `COMPONENT_STATUS.json`), release gate (fail-closed, MASTER.md presence check), reproducible build + CycloneDX SBOM, benchmark.
- 155 tests (from 15; 152 pass, 3 pk_core tests skip): fixtures per vendor/failure mode, property/fuzz, concurrency, fault injection, conformance, tooling.

### Defects found while building (fixed before release)
- Executor measured probe latency from *submission*, so probes queued behind the concurrency limit were falsely timed out and forced `unprobed`; latency is now measured from worker start (regression test `test_queued_probes_not_falsely_timed_out`).
- CPU engine listed `virt.slat` as a known x86 feature but the Linux flag table had no mapping for `ept`/`npt`, so every Linux host would have been reported SLAT-*absent*; mapped both flags.
- Windows `Get-Tpm` “present but not ready” mapped to proven-absent; now `unprobed` (E001).
- Broker client ran `python -I -m …`, which under 3.11 isolated/safe-path mode cannot import the package — every broker call failed as MALFORMED_RESPONSE; the package root is now injected explicitly.

### Not done (see COMPONENT_STATUS.json)
Independent sign-off (all 55), physical hardware lab (MC-42), real sibling integration (MC-21..26), pk_core 100-check package (MC-55), original MASTER.md (MC-54), owner-named ADR/policy (MC-49/50).

## 4.2.0 — 2026-09-22

Audit, functional completion, hardening, and packaging pass.

### Functional additions

- Added `capabilities.py` as a `pk_core`-independent three-valued capability state engine.
- Added `discovery.py` to collect privacy-minimized CPU, memory, storage, NIC/interface, adapter, virtualization, and TPM observations using read-only OS facilities.
- Added `ProbeSchedule` for bounded per-capability re-probe and explicit hot-add scheduling.
- Added `selftest.py` for bootstrap validation without the external control-plane package.
- Added four versioned JSON Schemas for probe, report, schedule, and hardware inventory interfaces.
- Added deterministic unit tests for discovery, report invariants, fail-closed probing, canonical signing bytes, freshness, and scheduling.

### Defects fixed

- Empty capability reports could be consumed while claiming valid freshness; empty reports now fail closed.
- Future-dated records could yield negative report age; consumer validation now rejects future probe timestamps.
- Mutable/corrupted `results` records could cause uncontrolled tuple-unpacking failures; structural validation now detects malformed records before consumer serialization.
- Node identifiers were not validated; node and capability identifiers now use the same bounded safe-label policy.
- Timestamps accepted booleans and unconstrained values; clock fields now require non-negative integers and explicitly reject `bool`.
- Probe failures lost their cause; bounded local diagnostics now retain unavailable/crash/ambiguous reasons without adding them to the signed v1 wire format.
- Signing used `repr()` of a consumer view containing dynamic `age`; signing bytes are now canonical JSON over stable report facts only.
- The contract used GAP-07 signing behavior without declaring GAP-07 as a dependency; the dependency is now explicit.
- The contract named re-probe scheduling as an owned behavior but provided no scheduling implementation; `ProbeSchedule` now supplies deterministic due/hot-add logic.
- Public interfaces were named but had no packaged machine-readable schema; schema files are now included.
- The README asserted that `MASTER.md` was included although it was absent from the supplied archive; the claim is corrected and provenance restoration is tracked as a remaining item.

### Hardening

- External command execution is shell-free, fixed-path, timeout-bounded, and output-bounded.
- Hardware inventory intentionally omits MAC addresses, IP addresses, serial numbers, disk contents, credentials, and secrets.
- GPU adapter enumeration is treated only as an observation; it does not become a schedulable `gpu=present` claim without a compute-runtime probe.
- NPU capability remains `unprobed` rather than inferred from platform/marketing identifiers.
- TPM scheduling capability is based on usable device exposure where supported, not merely an inferred platform claim.
- Package import degrades explicitly when `pk_core` is absent while preserving standalone discovery functionality.

### Validation in this package

- Python compile check: PASS.
- Dependency-free unit tests: PASS.
- Local discovery/self-test: PASS.
- External `pk_core` 100-requirement integration tests: not executable in the audit container because `pk_core` is not bundled/installed; the existing tests remain and report a skip rather than a false pass.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- `component.py`: every bare `assert` in the reference implementation and `assess_*` bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- `component.py`: expected-refusal checks fail if the refusal does not occur.
- `tests/test_component.py`: stdlib conformance test for 100 findings, optimized-mode parity, and version pin.
- `VERSION` file and `__version__` added.

### Defects fixed

- `CapabilityReport.age`: freshness now measures from the oldest probe timestamp so one fresh re-probe cannot launder stale entries.
- `CapabilityReport.record`: `published_at` no longer moves backwards and capability names are validated.
- `probe`: ambiguous and crashing probes now become `unprobed` instead of preserving or coercing a stale state.

## 4.0.0

- Initial master-applied component.
