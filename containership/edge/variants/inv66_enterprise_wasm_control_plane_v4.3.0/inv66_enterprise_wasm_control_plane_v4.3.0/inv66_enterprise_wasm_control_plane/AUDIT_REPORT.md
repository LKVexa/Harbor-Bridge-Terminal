# INV-66 Enterprise Wasm Control Plane — Audit & Hardening Report

## v4.3.0 remediation pass (2026-09-23)

**Input:** 4.2.0 archive + `INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (71 MC components, 1,420 items, 12 program gates).
**Output:** 4.3.0. The per-item record is generated in `governance/CHECKLIST_STATUS.md`; component dispositions and their evidence are in `governance/RTM.json`.

Headline: all 71 components now have an implementation or artifact plus an RTM disposition (PROG-01 met). 45 are closed in this archive
apart from human review / hosted CI; 25 are partially closed with the remainder waived to named external prerequisites; 1 (edge power, MC-048) is
not applicable. Across the 1,420 items: see totals in `CHECKLIST_STATUS.md`. The exit gate is **NO_GO** until the waived items close
(owners and approvals, pk_core conformance, real-dependency E2E, multi-node HA, hosted CI, operator drills).

Defects found and fixed *by* the new verification: RecursionError on deep nesting (fuzz), cross-process chain fork (multi-process race),
unbounded memory (bench RSS gate), non-monotonic config revision after rollback (service test), lease expiry during idle (governance test,
resolved by the maintenance loop's heartbeat).

---

## v4.2.0 record (retained)


**Input version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** repository parse, correctness audit, defensive hardening, version bump, isolated tests, and post-update missing-component audit.

## Initial findings

- The admission engine could still raise `KeyError` for a component with a valid image but no `name`, because rejection paths indexed `c['name']`.
- RBAC configuration was aliased through a caller-owned mutable dictionary and could be changed after control-plane construction.
- `audit` and `forwarded` were public mutable lists; callers could directly mutate live internal state.
- The audit chain covered decisions but did not bind the exact admitted manifest digest or an explicit monotonic sequence into each event.
- Audit hashing used ordinary JSON defaults instead of a compact canonical representation and had no domain separation.
- No component-count or manifest-size bounds protected the reference engine from straightforward memory/CPU abuse.
- Admission/audit/forwarding updates had no concurrency serialization, so multi-threaded callers could race on audit order/state.
- Signer and registry configuration accepted weakly validated values.
- The only bundled tests were all skipped when `pk_core` was unavailable, leaving the local decision engine untested in an isolated checkout.
- The README claimed `MASTER.md` was bundled, but the file was absent.

## Changes made in v4.2.0

- Extracted the security-critical local engine into dependency-light `control_plane.py` for isolated testing.
- Added strict policy configuration validation and defensive copies (`MappingProxyType`, `frozenset`).
- Added robust user/lattice/component-name validation and fail-closed malformed input handling.
- Added duplicate component-name rejection.
- Added configurable `max_components` and `max_manifest_bytes` admission limits.
- Added canonical JSON manifest hashing (`manifest_sha256`) and recorded byte/component counts with every decision.
- Added domain-separated, sequence-bound SHA-256 audit records.
- Replaced live mutable `audit`/`forwarded` exposure with defensive snapshots.
- Added `export_audit()` and validation of exported/tampered audit snapshots.
- Added an `RLock` around record/forward mutations to preserve coherent in-process ordering under concurrent callers.
- Updated component behavioral assessments to use defensive snapshots.
- Added 11 self-contained regression/security tests, including a 50-thread concurrent admission test.
- Bumped `VERSION`, `__version__`, README, and tests from 4.1.0 to 4.2.0.
- Corrected the README’s false `MASTER.md` packaging claim.
- Added this report, `MISSING_COMPONENTS.md`, and local `VERIFICATION.json` evidence.

## Verification performed

- `python -m compileall` — pass.
- `python -m unittest discover -s inv66_enterprise_wasm_control_plane/tests -v` — 11 local tests pass; 3 `pk_core` conformance tests skip because `pk_core` is not bundled/importable in this archive.
- `python -O tests/test_control_plane.py` — all 11 local tests pass in optimized mode.
- `VERIFICATION.json` — machine-readable local verification summary; it explicitly records that full `pk_core` conformance was not executable here.
- Static source scan for high-risk dynamic execution/shell/pickle patterns — no such runtime patterns identified in the local implementation.

## Important residual limitation

The audit hash chain is useful for mutation detection but is **not externally tamper-proof**. A privileged attacker who can replace the complete audit history can recompute an unkeyed SHA-256 chain. Production integrity requires durable append-only storage plus a protected signature/MAC or external transparency/WORM anchor. See MC-035.

## Post-update gap result

The second-pass audit identified **71 missing production components/artifacts**. They are enumerated with severity and checklist mapping in `MISSING_COMPONENTS.md`.
