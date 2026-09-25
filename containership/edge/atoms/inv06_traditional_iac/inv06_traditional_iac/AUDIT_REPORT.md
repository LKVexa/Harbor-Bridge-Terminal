# INV-06 Traditional IaC — Audit Report

**Input:** `inv06_traditional_iac.zip`  
**Audited/bumped version:** `4.2.0`  
**Audit date:** 2026-09-22

## Executive result

The supplied `4.1.0` archive was syntactically valid and internally small, but its reference state engine had several correctness and hardening gaps: authoritative state could be mutated without serial advancement, plan inputs could retain mutable aliases, apply was not synchronized across threads, plans lacked fail-closed structural/integrity validation, and drift detection could not distinguish a missing resource from a present JSON `null`. Its tests were also decorated so that when `pk_core` was absent, the entire test class—including version and behavior checks—was skipped.

Version `4.2.0` fixes those package-local defects, adds schema artifacts and standalone tests, and explicitly records the production capabilities still missing from the archive. The package remains a reference/master component rather than a complete production IaC control plane.

## Findings fixed in 4.2.0

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| F-001 | High | `resources` was a public mutable dictionary; callers could change authoritative state without advancing `serial`. | Authoritative state is private; `resources` returns a detached copy. |
| F-002 | High | `protected` was a public mutable set; protection policy could change outside serial/audit semantics. | `protected` is read-only to callers; `protect()`/`unprotect()` advance serial and audit the change. |
| F-003 | High | Check-then-apply had no synchronization, allowing concurrent plans to race around serial validation. | State transitions are serialized under `threading.RLock`; concurrency test proves only one same-serial plan commits. |
| F-004 | High | Plan/state values could alias caller-owned mutable objects and change after planning. | JSON-compatible values are detached/normalized before plan/state use. |
| F-005 | High | Plans had no strict schema/integrity validation. | Required/unknown fields, types, overlaps, duplicate deletes, schema version, identifiers, and SHA-256 digest are validated before mutation. |
| F-006 | Medium | Drift used `.get()`, conflating missing resources with legitimate JSON `null`. | Drift now records `state_present`/`real_present` flags. |
| F-007 | Medium | Failures were exception strings only. | Stable machine-readable error codes and structured details added. |
| F-008 | Medium | No package-local metrics or auditable operation chain. | Added counters and an in-memory SHA-256 audit chain with verifier. |
| F-009 | Medium | Tests could all be skipped when `pk_core` was unavailable. | Standalone engine tests run without `pk_core`; only parent-framework tests skip. |
| F-010 | Medium | README claimed `MASTER.md` was bundled when it was absent. | Claim removed; missing source artifact tracked as `MC-001`. |
| F-011 | Medium | No package-local typed schema artifacts for plan/state/drift payloads. | Added JSON Schema 2020-12 definitions and a reference fixture. |
| F-012 | Low | Importing the package failed in an isolated environment solely because `pk_core` was missing. | Core engine now imports independently; parent adapter reports unavailable until `pk_core` exists. |

## Validation performed

- ZIP input integrity: PASS.
- Python compilation (`compileall`): PASS.
- Standalone/unit tests: **12 passed**.
- Optimized interpreter (`python -O`) core behavior: PASS.
- Same-serial two-thread race test: PASS (one apply, one stale refusal).
- JSON schema documents: parse successfully.
- Parent `pk_core` conformance tests: **2 skipped**, because `pk_core` is not included in the isolated source archive.

## Certification limitation

The archive's `CHECKLIST.json` contains 100 requirements, but many are estate-level operational, security, integration, performance, and governance requirements. The package's parent-framework `Component` superclass is responsible for producing the complete 100-item assessment. Because `pk_core` and its evidence context are not bundled here, this audit does **not** claim an independently reproduced 100/100 production gate. `MISSING_COMPONENTS.md` enumerates the package/estate capabilities that are not present locally.

## Security note on plan digests

The SHA-256 plan digest in `4.2.0` detects accidental mutation or modification without resealing. It is **not** an authorization signature because no secret or signing identity is involved. A malicious actor able to construct and reseal arbitrary plans must still be constrained by the missing authentication, authorization, policy, provenance, and signed-audit components (`MC-033` through `MC-040`).

## Versioning rationale

The bump from `4.1.0` to `4.2.0` is a minor-version hardening release: the public package identity and `PK_IAC_* /1` interface family remain, while validation, isolation, schemas, observability, and test coverage are strengthened. Production-grade distributed backends and provider execution remain outside this archive and are tracked as missing components rather than being simulated as complete.


## Addendum — 4.3.0 checklist execution (2026-09-22)

- Checklist executed: 72 components, 4,830 controls (3,600 baseline, 510 component-specific, 720 Definition-of-Done).
- Outcome: 997 met package-locally; 65 draft (awaiting approval); 234 owner-required; 586 external; 50 blocked; 2,898 open. Definition-of-Done items are not self-certified.
- Tests: 14 (4.2.0 suite, 2 pk_core skips) + 61 new, all passing normally and under `python -O`.
- Defect found and fixed: F-013 (High). Replaying an applied plan under a new idempotency key would call the provider before the stale refusal, because the provider ran before `apply()`'s serial check. Fixed with `IacState.precheck()` before any provider call. Regression covered by `ControlPlaneTest.test_end_to_end_and_controls`.
- Gate: **NO_GO**. Blockers are MC-001 (source not supplied); MC-019/020/038/055/057/058 (external); evidence unsigned because no `INV06_EVIDENCE_KEY` was provided.
