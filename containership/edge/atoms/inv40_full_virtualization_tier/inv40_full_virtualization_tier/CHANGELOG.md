# Changelog - INV-40

## 4.3.0 - 2026-09-22

Applied `INV40_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST_v4.2.0.md` (6 repository components + 91 open requirements) through the junkyard chop shop.

- Added `fvt/` hardening layer (13 modules, stdlib only) and six versioned JSON schemas; reference runtime untouched.
- Added KVM-only QEMU/QMP provider adapter, host primitive probe, non-production fake provider with fault injection.
- Added config store (layering, provenance, atomic activation, auto/operator rollback, secret refusal), capability-token authn/authz, hash-chained audit, CRC-framed journal with crash recovery and backup/restore, retry/breaker/admission/quotas, fencing epochs, telemetry with explain view, pk_core API contract, protocol negotiation, production exit gate.
- Added `pyproject.toml`, CI workflow, `tools/ci.py`, fuzz and bench harnesses, bootstrap tool, traceability generator, docs (assumptions, owners, ADR, requirements, interfaces, versioning, configuration, threat model, failure modes, performance, observability, testing, operations), alerts/dashboard definitions, exceptions register.
- Tests: 15 → 85 (81 run, 4 lane-gated: 3 pk_core, 1 kvm). Only change to an existing test: the version literal in `test_runtime.RepositoryMetadataTest` (4.2.0 → 4.3.0, plus pyproject agreement).
- Defects found by this pass's own tests and fixed: D-01 concurrent boots of one guest each launched a hypervisor and the losers' cleanup tore down the winner; D-02 journal replay crashed (AttributeError) on a CRC-valid non-object record; D-03 the first fuzzer could not reach that path (CRC-framed input) — structure-aware lane added; D-04 config secret-key pattern matched `allow_gpu_passthrough` ("pass"); D-05 `QemuKvmProvider.argv` guarded TCG with `assert` (stripped under -O) — now explicit.
- Result: 59 IMPLEMENTED / 37 PARTIAL / 10 BLOCKED / **0 CLOSED** of 106; gate NO_GO.

## 4.2.0 - 2026-09-22

Audit, correctness, hardening, and evidence-integrity pass.

### Correctness and isolation fixes

- Moved the critical VM model into dependency-free `runtime.py` so it can be tested without `pk_core`.
- Made package-level `pk_core` integration lazy, so importing the package/runtime and collecting tests no longer fails when the external framework is absent.
- Replaced the incorrect `device_conflict()` name-based check with concrete device-instance ownership semantics.
- Added a thread-safe `DeviceLeaseRegistry` that rejects sharing a concrete device instance across distinct live VMs and releases leases on stop/destroy.
- Enforced the complete baseline full-device model; callers can add devices but cannot silently remove mandatory ones.
- Added strict validation for VM/tenant identity, integer resource metrics, and the hardware-primitive boolean.
- Added explicit `created -> running -> stopped/destroyed` lifecycle guards, restart support from `stopped`, terminal destruction, and idempotent repeated destroy.
- Corrected the previous semantic contradiction where `stop()` returned `destroyed=True` while setting state to `stopped`.
- Added explicit `degraded` boot status when the boot budget is exceeded instead of hiding the SLO miss.
- Added machine-readable `PK_FULL_VM_ERROR/1` error codes and `PK_FULL_VM_STATE/1` stop/destroy results.

### Verification hardening

- Added standalone unit tests for validation, primitive refusal, footprint refusal, lifecycle transitions, boot-budget reporting, device sharing, lease release, and a concurrent lease race.
- Standalone tests run under both normal Python and `python -O`; they do not depend on optimizer-sensitive assertions.
- The `pk_core` conformance suite remains conditional because `pk_core` is not bundled in this archive; the updated audit no longer treats those skipped tests as proof of 100/100 conformance.

### Evidence and documentation

- Version bumped from 4.1.0 to 4.2.0.
- Removed the inaccurate README claim that `MASTER.md` is bundled; the file is absent.
- Added post-update audit and complete open-gap inventory (`AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`, `MISSING_COMPONENTS.json`).

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::FullVm.start: non-positive memory_mib and negative boot time/footprint accepted and reported -> ValueError
- component.py::device_conflict: condition 'a.name == b.name' looks suspect but semantics ambiguous and unused; left unchanged

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
