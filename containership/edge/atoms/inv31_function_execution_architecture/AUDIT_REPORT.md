# INV-31 Audit / Fix / Harden / Version-Bump Report

**Input version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22

## Initial audit findings

1. **Concurrent scratch-state corruption risk:** all in-flight invocations on an instance shared one `scratch` dictionary, and `leave()` cleared the entire dictionary. With concurrency greater than one, one request could erase another request's state.
2. **No synchronization around concurrency accounting or pool mutation:** the implementation modeled concurrent admission but did not lock the check/increment/state transitions.
3. **Unbounded pool growth:** new tenant/version combinations could create instances without a hard local safety ceiling.
4. **Clock rollback leak/unsafe-age handling:** negative age was excluded from warm reuse but such idle instances were not proactively removed, allowing pool growth until the logical clock caught up.
5. **Mutable security identity:** tenant/version/name/creation time were ordinary writable dataclass attributes despite the documented whole-life binding rule.
6. **Weak input/configuration validation:** truthiness checks rejected empty strings but accepted whitespace-only identifiers, control characters, arbitrary identifier length, booleans as integer time, and invalid runtime limit values.
7. **Missing implemented `pool` interface:** the contract declared `PK_FUNCTION_POOL/1`, but the runtime had no public method that emitted that interface.
8. **No machine-readable interface schemas:** interface names were strings in the contract only.
9. **Evidence-to-checklist misalignment:** several behavioral findings were assigned to unrelated checklist slots. Most notably, concurrency refusal was written to C056 (degraded operation), warm reuse was written to C036 (configuration provenance), and version mismatch reuse behavior was used as evidence for C045 (artifact signature/digest/provenance verification).
10. **False-green test shape when `pk_core` is absent:** the class-level skip caused every test, including version checks, to skip when the external framework was unavailable.
11. **Documentation integrity error:** README claimed `MASTER.md` was bundled, but the file was absent.
12. **Framework dependency not self-contained:** `component.py` and `contract.py` require `pk_core`, which is not included in the archive.

## Corrections applied in 4.2.0

- Added dependency-free `runtime.py` and kept `component.py` as the `pk_core` conformance adapter.
- Implemented per-invocation scratch scopes and scope-specific cleanup.
- Added lock-protected instance/pool transitions and a threaded concurrency regression test.
- Made instance identity immutable after initialization.
- Added validated runtime configuration for concurrency, max age, and max instances.
- Added bounded pool capacity with safe idle eviction and fail-closed `PoolCapacityExceeded` when all slots are active.
- Added negative-age/clock-rollback eviction.
- Added safe `destroy_idle()` drain/quarantine behavior.
- Added `PK_FUNCTION_POOL/1` diagnostics and stable warm/cold decision reasons.
- Added JSON Schemas for both public interface payloads.
- Corrected evidence mappings to requirements actually exercised by the code.
- Added standalone safety tests that run even when `pk_core` is absent.
- Added architecture, interface, security, configuration, dependency, and operations notes.
- Corrected README packaging claims and bumped all version references to 4.2.0.

## Verification performed

- Normal Python stdlib suite: **14 passed**, **3 skipped** (`pk_core` dependent only).
- Optimized Python (`python -O`) suite: **14 passed**, **3 skipped** (`pk_core` dependent only).
- `compileall`: **PASS**.
- `CHECKLIST.json` integrity: **100 items**, unique IDs/ordinals, exact INV-31-C001..C100 sequence.
- JSON parsing: checklist and both new interface schemas **PASS**.
- Source scan: no `eval`, `exec`, `pickle`, `shell=True`, `os.system`, or bare production `assert` usage found.

## Certification limitation

The parent 100-item `pk_core` conformance/evidence gate was **not executable** from the supplied archive because `pk_core` is absent. Therefore this audit does not claim a production-GO certification. `MISSING_COMPONENTS.md` and `POST_AUDIT.json` conservatively enumerate the remaining production gaps.
