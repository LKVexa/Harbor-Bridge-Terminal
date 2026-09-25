# INV-40 Repository Audit Report

**Artifact:** `inv40_full_virtualization_tier`  
**Input version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22

## Executive result

The repository was parsed, corrected, hardened, version-bumped, and re-audited. The 4.2.0 runtime model passes all standalone tests in normal and optimized Python. The external `pk_core` conformance suite cannot be executed from this archive because `pk_core` is not bundled/importable; its three tests are therefore reported as skipped, not as proof of conformance.

The post-update evidence audit finds **9 requirements fully evidenced, 26 partially evidenced, and 65 missing**, leaving **91 of 100 checklist requirements not fully evidenced**. A complete item-by-item inventory is in `MISSING_COMPONENTS.md` / `.json`.

## Defects fixed

1. **Incorrect device-sharing detection (security/correctness):** the old `device_conflict()` required equal guest names and therefore failed to model concrete device ownership. 4.2.0 tracks device-instance IDs and uses a thread-safe lease registry.
2. **No enforcement point for device exclusivity:** 4.2.0 claims/rejects/releases concrete device leases during VM lifecycle operations and includes a concurrent race test.
3. **Lifecycle contradiction:** old `stop()` returned `destroyed=True` while setting `state=stopped`. 4.2.0 separates stop from terminal destroy and guards illegal transitions.
4. **Incomplete-device downgrade:** callers could replace the full device model with an arbitrarily small set. 4.2.0 requires the complete baseline model while still permitting additive devices.
5. **Weak input typing/identity validation:** VM name, tenant, metrics, primitive flag, and instance mappings are now validated strictly.
6. **Opaque failure signaling:** operational failures now have stable `PK_FULL_VM_ERROR/1` codes; state operations use `PK_FULL_VM_STATE/1`.
7. **Boot SLO visibility:** budget misses now return explicit `status=degraded`.
8. **All-tests-skipped false confidence:** the prior isolated test command could exit 0 with all conformance tests skipped when `pk_core` was absent. 4.2.0 adds 15 standalone runtime tests (plus 3 conditional pk_core tests) so core behavior is always exercised.
9. **README evidence mismatch:** the README claimed `MASTER.md` was bundled although it is absent. The claim was removed and the missing source artifact is recorded explicitly.
10. **Eager optional-dependency import:** package import/pytest collection previously failed when `pk_core` was absent. Integration symbols are now lazy-loaded, while the standalone runtime remains importable.

## Verification performed

- Python bytecode compilation: PASS.
- `python -m unittest discover -s tests -v`: PASS for standalone tests; pk_core-dependent tests SKIPPED because dependency is absent.
- `pytest -q`: PASS (15 standalone tests passed, 3 pk_core-dependent tests skipped).
- `python -O tests/test_runtime.py -v`: PASS.
- Concurrent duplicate-device lease race: PASS (exactly one claimant succeeds).
- ZIP path traversal inspection on the supplied archive: PASS (no absolute/parent-traversal entries found).

## Production-readiness conclusion

4.2.0 is materially safer and more internally consistent, but it is **not production-complete**. The archive lacks a real hypervisor/provider adapter, authentication/authorization, configuration management, distributed fencing, telemetry, release engineering, compatibility testing, performance certification, operational runbooks, and most production governance artifacts. The complete gap list is authoritative in `MISSING_COMPONENTS.md`.

---

## 4.3.0 addendum (2026-09-22)

Scope: the 97 open items of `INV40_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST_v4.2.0.md` plus the 9 present requirements, all traced in `traceability/requirements.json` (106 entries).

| Status | Count | Meaning |
|---|---|---|
| IMPLEMENTED | 59 | code/docs present and exercised by non-skipped tests in this build |
| PARTIAL | 37 | implemented portion tested; named blockers cover the rest |
| BLOCKED | 10 | needs an external input (owner, licence, KMS, adjacent layers, edge hardware, elapsed time) |
| CLOSED | 0 | closure needs a named accountable owner and independent review; none exists |

Verification (cloud container, CPython 3.11.15, no `/dev/kvm`, no QEMU): `tools/ci.py` → INCOMPLETE (exit 3): 85 tests, 81 passed, 0 failed, 0 mandatory skips; lanes `pk_core` (3) and `kvm` (1) NOT_RUN; `-O` run OK; wheel builds from declared metadata and imports from the installed copy with pk_core absent; fuzz 40,000 iterations, 0 unclassified crashes; bench p99 create/boot recorded against PROPOSED thresholds; gate NO_GO.

Not claimed: any hardware behaviour of the QEMU adapter; any pk_core conformance; encryption; multi-node fencing/failover; any drill, soak, or fleet result.
