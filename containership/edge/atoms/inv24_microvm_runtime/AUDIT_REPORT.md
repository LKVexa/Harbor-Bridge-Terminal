# INV-24 MicroVM Runtime — Audit Report

**Input version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-23

## Initial findings

- The package could not be imported without the external `pk_core` framework because `__init__.py` eagerly imported framework integration.
- All three original tests skipped when `pk_core` was unavailable, giving no local executable evidence for the safety-critical microVM state model.
- Runtime configuration could be mutated after construction, allowing tenant/device/resource/state changes that bypassed constructor validation and contradicted the claimed single-tenant/minimal-device invariants.
- Only minimum vCPU/memory limits existed; no maximum resource ceilings were enforced.
- Scalar validation accepted Python type-confusion cases such as booleans as integers; identifier validation did not reject whitespace/control-character edge cases.
- Stop/destruction was not terminal against repeated stop calls.
- The public create schema named in the contract had no corresponding local record method; there was no simple status snapshot.
- README claimed `MASTER.md` was present, but the archive did not contain it.
- No Firecracker executable/adapter or actual hypervisor integration is contained in the repository; the package is a domain/reference component rather than a working VMM runtime.

## Changes applied in 4.2.0

- Added framework-independent `runtime.py` and lazy framework loading.
- Added strict identifier/type/range validation.
- Added vCPU/memory upper and lower ceilings.
- Sealed all runtime-managed fields after initialization; lifecycle methods use controlled internal transitions.
- Added explicit creation and status records.
- Enforced terminal destruction semantics.
- Added 10 standalone unit tests and updated framework version checks.
- Corrected README artifact claim and documented framework dependency.
- Added this audit report and a complete post-update missing-components inventory.

## Verification performed

- `python -m unittest -v tests/test_runtime.py`: **10/10 passed**.
- `python -m py_compile __init__.py runtime.py component.py contract.py tests/test_runtime.py tests/test_component.py`: **passed**.
- Standalone package import without `pk_core`: **passed**.
- Direct access to framework integration without `pk_core`: correctly reports missing external dependency.
- Original framework conformance suite: **not executable in this isolated archive** because `pk_core` is absent; tests skip rather than fail.

## Readiness conclusion

Version 4.2.0 is materially safer and independently testable as a microVM lifecycle/configuration domain model. It is not, by itself, a production microVM runtime: executable Firecracker/KVM/device/control-plane integration, security controls, resilience mechanisms, telemetry, certification, release operations, and production evidence remain missing. See `MISSING_COMPONENTS.md` for the exhaustive repository-local gap inventory.

---

## 4.3.0 pass (2026-09-23) — missing-component checklist executed

- Input: 4.2.0 hardened archive + `INV24_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (64 components, 1,155 task IDs).
- Local implementation: see `../docs/CLOSURE_REPORT.md` (COMPLETE / PARTIAL / DOCUMENT_ONLY / NONE per component).
- Verification: 89 PASS, 0 FAIL, 9 NOT_TESTED; full suite also passes under `python -O`.
- Defect found and fixed during the pass: non-ASCII MAC → `TypeError` in `security/keys.py::Keyring.verify` (fuzzer).
- Gate: `evidence/production-gate.json` — **NO_GO**. Every component remains checklist status `BLOCKED` until owners/approvers are named, artifact pins approved, and real-host evidence produced.
