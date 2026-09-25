# Changelog - INV-45

## 4.3.0 - 2026-09-22

Remediation pass against the *INV-45 v4.2.0 Comprehensive Remediation Checklist* (junkyard chop-shop,
work order `inv45_sfi_mechanisms-20260922`). All new code is stdlib-only except Ed25519 (`cryptography`).

### Enforcement boundary (C031, C046, A3)

- `production/wasm.py`: strict Wasm 1.0 parser, full operand/control-stack type validator, encoder; pinned
  feature profile; limits and cooperative deadline; every failure is a registered `SfiError`.
- `production/sfi.py`: profile `PK-SFI-WASM32-MVP-1` (linear block partitioning + heap masking), rewriter,
  independent verifier with deterministic `PK_SFI_PROOF/1`; constant-address folding re-proven by the verifier.
- `production/trust.py`, `authz.py`, `service.py`: secret references, HMAC sealed descriptors, Ed25519
  artifact statements, capability authorization, replay protection, anti-rollback, and a trusted loader
  that re-binds digest, profile, config, tenant and version at load.
- `production/engine.py` + `engine_runner.js`: V8 via `node --permission`, one process per job, empty env,
  host-import allowlist, hard timeout.

### Operations and governance

- Config generations with secure defaults, overlays, provenance, atomic CAS activation and rollback;
  durable quarantine/anti-rollback state with owner fencing; admission control, retry, circuit breaker;
  hash-chained audit; metrics, structured logs, W3C trace propagation, explain records; health surface.
- Docs: ADR, assumptions/unsupported matrix, interfaces, compatibility, performance, SPEC (SHALL), RTM,
  threat model, capabilities, crypto policy, failure model, runbooks, SLO/telemetry, lifecycle policies,
  ownership (roles UNASSIGNED), waivers, MASTER.md, CODEOWNERS (placeholders), LICENSE-STATUS.md.
- Tooling: `tools/ci.py` lanes, `rtm.py`, `gen_docs.py`, `gen_fixtures.py`, `perf_gate.py`, `release.py`
  (SBOM, manifest, provenance, evidence, exit gate), `check_docs.py`, `fuzz_campaign.py`; GitHub workflow.

### Defects found and fixed during this pass

1. `__init__.py` hard-imported `pk_core`, so the package (and the "standalone" core) could not be imported
   without it - now optional, with `PK_CORE_ERROR`.
2. Audit log directory was never created: every event silently spooled; caught because health reported
   `degraded`.
3. Verifier accepted a growable table (`max` absent) although the profile requires `min == max`; caught by
   the fixture generator's expectation check.
4. Concurrent config activations could overwrite a generation file so the active pointer referenced the
   losing writer's content; activation now holds the lock before numbering and creates generations
   exclusively.
5. Descriptor and artifact-statement fields were used before type checks (`TypeError` escaped on a dict
   `key_id`); caught by the descriptor fuzzer, now strictly typed.
6. `br_table` validation copied the operand stack per target (quadratic; a 65 536-target table over a deep
   stack could run far past the deadline inside one instruction); now peek-based and linear.

### Honest results

- Perf gate FAILS PERF-01: worst-case load-bound masking overhead ~33-38 % (> 15 % contract SLO);
  compute-mixed ~0 %.
- Exit gate NO_GO; `pk_core` lane NOT RUN; license lane NOT RUN; all waivers pending approval.

## 4.2.0 - 2026-09-22

Audit, correctness, security-hardening, and evidence-integrity pass.

### Security and correctness

- Added dependency-free `sfi_core.py` so the SFI invariants can be tested without the external `pk_core` framework.
- Made `Access` and `SandboxRegion` immutable and added strict validation for malformed offsets, flags, region bases, and region sizes.
- Copied caller-owned access and branch-target collections into immutable containers to prevent post-construction policy widening through alias mutation.
- Replaced the old access-object identity check with a verification seal over the complete security-sensitive state: region, access manifest, and indirect-target policy.
- A failed re-verification now clears the old seal before checking new state, preventing stale verification from surviving a failed update.
- Added `ModuleNotVerified` fail-closed behavior and stable machine-readable security error codes/details.
- Added versioned JSON Schema documents for `PK_SFI_MODULE/1` and `PK_SFI_MASK/1`.

### Evidence integrity

- Removed the C036 false positive where access-verification behavior was reported as configuration-provenance evidence.
- Removed the C047 false positive where unmasked-access rejection was reported as encryption evidence.
- Removed the C043 false positive where branch-target confinement was reported as ambient-authority evidence.
- Removed resilience-slot overwrites that reported region validation/unverified access as evidence for unrelated C051/C057 requirements.
- Kept concrete reference-model isolation evidence only on C046, which is the requirement it actually supports.
- README no longer claims the absent `MASTER.md` file is bundled.

### Tests and audit material

- Added standalone security regression tests for confinement, invalid inputs, alias mutation, verification invalidation, failed re-verification, branch confinement, machine-readable errors, version consistency, and schema IDs.
- Added `SECURITY.md` documenting trust boundaries and production limitations.
- Added `MISSING_COMPONENTS.md` with the post-hardening re-audit of outstanding production components/evidence.

### Validation

- Python bytecode compilation passes.
- Standalone SFI core unit tests pass in normal and optimized (`python -O`) modes.
- Full `pk_core` conformance/gate execution cannot be proven from this archive alone because `pk_core` is not bundled in the uploaded repository.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O`.
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen.
- tests/test_component.py: stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::SfiModule.branch: usable before verification -> requires verification.
- component.py::SfiModule.access/branch: replacing accesses after verify kept verified=True -> verified snapshot must be the loaded accesses.

### Historical gate claim

The 4.1.0 notes stated that all 100 requirements were satisfied. The 4.2.0 audit
found misindexed evidence assignments and missing production artifacts, so that
historical statement must not be used as current proof of full checklist
completion.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
