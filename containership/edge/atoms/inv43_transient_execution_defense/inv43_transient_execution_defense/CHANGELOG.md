# Changelog - INV-43

## 4.3.0 - 2026-09-22

Execution of the 52-item `INV43_v4.2.0_MISSING_COMPONENT_REMEDIATION_CHECKLIST.md` (copied under `remediation/`). Result: 21 LOCAL_IMPLEMENTED, 27 PARTIAL, 4 BLOCKED; local production gate **NO_GO**. Nothing is marked complete: every item still needs independent review, and the items that need an owner, pk_core, hardware or a lab name exactly what is missing.

### New runtime components (stdlib only)
- `collector.py` sysfs read-back with freshness metadata; fail-closed classifier (`Mitigation: … Vulnerable` = inactive; unknown formats = unknown; unreadable SMT = on).
- `attestation.py` HMAC envelopes: node-bound keys, sequence replay protection, expiry, skew bound, rotation/revocation.
- `authz.py` capability model; `policy.py` + sealed `policy/default_policy.json`; `config.py` layered tighten-only config with transactional activation/rollback.
- `registry.py` fleet registry (freshness, epochs, restart-closed, quarantine/freeze restored from the audit chain, explain records); `placement.py` SCH-01 adapter; `service.py` HTTP boundary; `negotiation.py`; `auditlog.py`; `resilience.py`; `telemetry.py`; `rollout.py`.
- `defense.py`: `not_affected` status, `PK_MITIGATIONS/2`, v1 refuses what it cannot express, lock + single-snapshot evaluation.
- New schemas: `PK_MITIGATIONS_2`, `PK_READBACK_1`, `INV43_CONFIG_1`, `INV43_POLICY_1`; `PK_ERROR_1` code enum widened, optional `decision_id` added.

### Evidence, supply chain, governance
- `tools/build_release.py`: verification runs (normal, `-O`, strict core), benchmark + threshold gate, real host read-back, governance report, hash-chained evidence ledger, STATUS/TRACEABILITY, CycloneDX SBOM, SHA256SUMS, in-toto statement, Ed25519 signature (**ephemeral dev key**), `conformance/INV43_LOCAL_GATE.json`.
- `tools/verify_release.py`, `tools/verify_governance.py`; `pyproject.toml`, `requirements-dev.lock`, `deps/pk_core.lock.json` (UNRESOLVED).
- Docs: ADR-0001 (PROPOSED), ADR-0002 SFI resolution (PROPOSED), threat model, concurrency, compatibility matrix, recovery, capacity, runbook, incident response, `SECURITY.md`; `ops/alerts.yaml`, `ops/dashboard.json`; `governance/` owners (unassigned), review cadence, exception ledger.

### Defects found by this pass's own tests and fixed
1. `report()` summed `total_cost_percent` from a second snapshot: 2,682 torn reports in 0.4 s under concurrent writes.
2. A `NaN` measured cost passed the `cost <= 0` guard and crashed intake with a bare `ValueError` (would have been an HTTP 500); now `unknown` + structured `bad_request`.
3. Workload ids carrying tenant names were logged in clear text although tenants were pseudonymised.
4. `not_found` was outside the failure taxonomy and would have been classed `software_defect` (false paging).
5. The file-backed audit log kept every event in memory forever (found by the capacity benchmark).
6. `verify.py` used `compileall`, which wrote `__pycache__` into the package it was verifying; now compiles in memory.
7. The evidence-path test caught `tools/verify_release.py` referenced by the status table before it existed.

### Real-host finding
The build host's kernel reports `spectre_v2: Mitigation: Enhanced / Automatic IBRS; …; BHI: Vulnerable`. The collector classifies it `inactive`, so that host refuses cross-tenant co-tenancy (`evidence/host_readback.json`).

## 4.2.0 - 2026-09-22

Second audit, correctness, hardening, and verification pass.

### Runtime and policy hardening

- Split the standalone security policy model into `defense.py`; importing the package and exercising policy no longer requires `pk_core`.
- Added strict validation for node, tenant, and mitigation identifiers, boolean posture flags, initial mitigation maps, status values, finite costs, boolean-as-number mistakes, and stale nonzero cost on inactive/unknown records.
- Preserved the 4.1.x mitigation tuple representation while revalidating caller-supplied initial state.
- Added caller-selectable required mitigation sets. Unknown future mitigation requirements fail closed rather than being silently ignored.
- Added stable `required_mitigation_missing` and `unsafe_smt` refusal codes plus a versioned `PK_ERROR/1` representation.
- Switched active-cost summation to `math.fsum` before rounding.

### Contract correctness

- Fixed `PK_MITIGATIONS/1`: the status report now includes the promised per-mitigation status and measured cost, not merely active names and an aggregate.
- Added `required_for_cotenancy` / `required_mitigations` to make the evaluated policy input explicit.
- Added Draft 2020-12 JSON Schemas for `PK_MITIGATIONS/1`, `PK_COTENANCY/1`, and `PK_ERROR/1`, with reference fixtures.
- Corrected runtime evidence references after moving the model to `defense.py`.

### Verification hardening

- Added standalone tests that run even when `pk_core` is unavailable.
- Restricted skips to the external registry conformance tests; package/version/policy tests no longer disappear with the dependency.
- Added `PK_REQUIRE_CORE=1` release mode to make a missing external registry runtime a failure.
- Added `verify.py` and a Windows-safe `VERIFY.cmd` launcher.
- Added an unsigned SHA-256 file manifest for corruption detection (not a substitute for signed provenance).
- Added a static no-bare-assert check for runtime modules and repository compile verification.

### Documentation and audit integrity

- Removed the false README claim that an absent `MASTER.md` was present.
- Replaced the unconditional production-certification wording with an explicit remaining-components audit in `AUDIT_REPORT.md`.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen.
- tests/test_component.py: stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::MitigationState.record: NaN/inf/negative cost accepted (NaN passed the active>0 check) -> finite non-negative required.

### Historical gate claim

The 4.1.0 changelog reported all 100 requirements satisfied under python and python -O. The 4.2.0 audit found that the supplied archive did not contain `pk_core`, so those conformance tests skip in isolation and cannot independently substantiate that production-readiness claim.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
