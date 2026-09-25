# INV-03 Container Hardening - Audit Report

**Audited input:** `inv03_container_hardening`  
**Input version:** 4.1.0  
**Remediated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** parse, static audit, security logic review, fail-closed repair, hardening, tests, documentation consistency, version bump, and missing-component inventory.

## Executive result

Version 4.2.0 repairs a real fail-open admission defect and several malformed-input/exception edge cases in the existing five-control evaluator. The security-critical logic is now isolated in `policy.py`, has no `pk_core` dependency, exposes an immutable control registry, produces self-describing decisions, supports JSON-safe exception encodings, and fails closed on malformed interface inputs.

The archive is still **not a complete production container-isolation system**. The most important open gap is that the checklist calls for stronger isolation using gVisor/user-space kernels, but the package does not yet discover, pin, select, or enforce a sandbox runtime. The complete open inventory is in `MISSING_COMPONENTS.md`.

## Parsed package inventory

The input contained 8 files plus package/test directories:

- `contract.py`
- `component.py`
- `CHECKLIST.json`
- `__init__.py`
- `README.md`
- `CHANGELOG.md`
- `VERSION`
- `tests/test_component.py`

Version 4.2.0 adds:

- `policy.py`
- `tests/test_policy.py`
- `AUDIT_REPORT.md`
- `MISSING_COMPONENTS.md`

## Findings and remediation

| ID | Severity | Finding | 4.2.0 action |
|---|---|---|---|
| INV03-A01 | Critical | `not-privileged` used `not spec.get("privileged")`; an omitted field therefore passed the control. | Fixed. `privileged` must be explicitly present and literal `False`. |
| INV03-A02 | High | Top-level malformed `spec`, `exceptions`, workload ID, or time values could raise or behave inconsistently instead of producing a deterministic denial. | Fixed. Interface errors are recorded in `input_errors` and force `admit=False`. |
| INV03-A03 | High | Capability fields could be malformed while relying on loose containment/truthiness semantics. | Fixed. `capabilities` must be a mapping; `drop` and `add` must be string lists; `ALL` must be dropped; `add` must be empty. |
| INV03-A04 | High | Python booleans are integers; `expires=True` could satisfy an integer type test under some timestamps. | Fixed. Timestamp validation explicitly excludes booleans. |
| INV03-A05 | High | Exception revocation was not modeled. | Hardened. Any non-false/non-null `revoked` value prevents the waiver from being honored. |
| INV03-A06 | Medium | The only exception encoding used tuple dictionary keys, which is not directly JSON serializable for a wire/file contract. | Fixed compatibly. Tuple-keyed maps remain accepted; nested maps, composite keys, and list records are also accepted. |
| INV03-A07 | Medium | The exported control dictionary was mutable, allowing in-process replacement/removal of checks. | Fixed. The published registry is a `MappingProxyType`. |
| INV03-A08 | Medium | Evaluation output did not identify the baseline/schema that made the decision. | Fixed. Results include `schema` and `baseline_version`; `get_baseline()` exposes the effective control set. |
| INV03-A09 | Medium | Security logic lived inside the framework component, making isolated testing difficult when `pk_core` was unavailable. | Fixed. Admission policy moved to dependency-free `policy.py`. |
| INV03-A10 | Medium | `README.md` stated that `MASTER.md` was included, but the archive did not contain it. | Fixed documentation. The false claim was removed; the missing artifact is recorded as an open package gap. |
| INV03-A11 | Medium | The 100-requirement checklist can be syntactically complete even when concrete runtime integrations do not exist. | Documented. `MISSING_COMPONENTS.md` separates declared requirements from implemented subsystems. |
| INV03-A12 | Open / Critical | No gVisor/runsc/user-space-kernel discovery, version pin, runtime-class enforcement, health check, or admission binding exists. | Not fabricated. Listed as the first production gap. |
| INV03-A13 | Open / High | `pk_core` is external and not bundled or dependency-pinned in this archive, so full framework conformance cannot execute here. | Recorded as an integration/packaging gap; dependency-free policy tests were added. |

## Verification performed

- `python -m compileall -q inv03_container_hardening` - PASS.
- Dependency-free `tests/test_policy.py` - PASS, 10 tests.
- Dependency-free `tests/test_policy.py` under `python -O` - PASS, 10 tests.
- `CHECKLIST.json` parse - PASS.
- Checklist cardinality - PASS: exactly 100 items.
- Checklist identity - PASS: 100 unique `check_id` values.
- Checklist ordering - PASS: ordinals 1 through 100 without gaps.
- Framework test file parses/runs, but all framework-dependent tests SKIP when `pk_core` is not importable. This is intentionally not reported as a conformance pass.

## Local performance sanity check

A local, non-certifying microbenchmark of 30,000 hardened-spec evaluations measured approximately:

- p50: 0.0021 ms
- p95: 0.0022 ms
- p99: 0.0026 ms
- maximum observed: 0.2754 ms

This demonstrates that the pure-Python policy function is comfortably below the contract's 5 ms evaluation target in this environment, but it does **not** certify end-to-end admission latency under production orchestrator load.

## Version decision

The package was bumped from **4.1.0 to 4.2.0**. The public evaluator retains its original required arguments and original result fields (`workload`, `admit`, `failed`, `excepted`) while adding metadata/error fields and tightening fail-open behavior. The change is therefore treated as a security-hardening minor release in the existing project convention.

## Remaining certification boundary

Do not interpret the 4.2.0 package as production-complete until at minimum the P0/P1 items in `MISSING_COMPONENTS.md` are implemented and the full framework/orchestrator integration suite runs against the real `pk_core`, container runtime, admission path, node fleet, and supported architecture matrix.


---

# Addendum — 4.3.0 checklist application (2026-09-22)

**Input:** 4.2.0 archive (all 12 files matched the 4.2.0 `RELEASE_MANIFEST.json` sha256 values on arrival) plus
`inv03_container_hardening_v4.2.0_PROFESSIONAL_COMPONENT_CHECKLIST.md` (70 components, 4,463 lines).

**Result:** 51 LOCAL_VERIFIED / 12 PARTIAL / 7 BLOCKED / **0 complete**; release gate **NO_GO** (exit 3).
Checks: unit (normal and `-O`) PASS, mutation probe 10/10 PASS, ruff PASS, mypy PASS, framework
conformance SKIPPED (no `pk_core`) — a skip is recorded as not-PASS.

**Why nothing is complete:** each component's required evidence package includes integration evidence
in the real orchestrator/runtime and a named approving owner. No cluster, gVisor node, KMS or owner was
available, and none was simulated as if it were. Every blocker is named per component.

**Defects found by this pass's own checks:** see CHANGELOG 4.3.0 → "Fixed during the pass".
