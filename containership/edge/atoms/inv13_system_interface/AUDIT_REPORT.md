# INV-13 System Interface — Audit Report

**Audited input:** `inv13_system_interface.zip`  
**Input version:** 4.1.0  
**Hardened version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** package integrity, implementation semantics, privilege boundaries, path confinement, state mutability, verification coverage, release truthfulness, and production-readiness gaps.

## Executive result

The 4.1.0 package was a coherent reference model with valid archive paths and syntactically valid Python, but it had a **high-severity post-validation authority-mutation flaw**: `World` was frozen as a dataclass while retaining the caller's mutable `set` object unchanged. A caller could therefore construct an allowed world, mutate the original set later, and silently add a new capability without re-running validation.

The package also exposed its preopen mapping as a directly mutable dictionary, accepted ambiguous/noncanonical preopen roots, silently overwrote existing preopens, lacked bounded input/resource growth, and described lexical string checks more strongly than the implementation warranted at an actual host filesystem boundary.

Version 4.2.0 closes those reference-model defects, adds dependency-free security regression tests and deterministic hash-chained security events, and documents the production boundary accurately. It remains **not a complete production WASI host**; the concrete missing components are enumerated in `MISSING_COMPONENTS.md`.

## Package parse/integrity

| Check | Result |
|---|---|
| ZIP traversal paths | PASS — no absolute or `..` archive members |
| Duplicate archive members | PASS |
| ZIP symlink members | PASS — none observed |
| Python syntax / bytecode compile | PASS |
| Version file / Python version pin | FIXED to 4.2.0 consistently |
| Core dependency availability | `pk_core` is external/not contained in this ZIP |
| Independent security-testability | FIXED — `runtime.py` has no `pk_core` dependency |

## Findings and remediation

| ID | Severity | 4.1.0 finding | 4.2.0 disposition |
|---|---|---|---|
| A-01 | High | `World(capabilities=<mutable set>)` retained the set; external mutation widened authority after validation. | **FIXED.** Capabilities are copied into a validated `frozenset`. |
| A-02 | High | `Instance.preopens` was caller-mutable; code could inject or retarget host roots without `grant_preopen()`. | **FIXED.** Internal mapping is private and exposed only through a read-only view. |
| A-03 | High | Existing logical preopens were silently overwritten, allowing accidental authority retargeting. | **FIXED.** Different-root replacement requires explicit `replace=True`; revocation is explicit. |
| A-04 | Medium | Host roots such as `/srv/../etc`, `//host/share`, or NUL-containing values were accepted or ambiguously represented. | **FIXED.** Canonical, single-rooted POSIX paths are required and bounded. |
| A-05 | Medium | World/component/capability/path inputs had incomplete type and length validation. | **FIXED.** Strict type/nonempty/NUL/length checks added where applicable. |
| A-06 | Medium | No preopen-count bound existed; untrusted configuration could grow authority/state without a local ceiling. | **FIXED.** `MAX_PREOPENS` added and enforced. |
| A-07 | Medium | Denial history was directly mutable and incomplete as an audit mechanism. | **FIXED/PARTIAL.** Read-only denial snapshots plus deterministic SHA-256 hash-chained events were added. Durable external storage/export remains missing. |
| A-08 | Medium | Path confinement wording could be read as host-filesystem confinement, but implementation performed lexical string normalization only. | **FIXED IN SCOPE.** `resolve()` now explicitly reports `lexical-posix`; README/code document descriptor-relative host resolution as a required production component. |
| A-09 | Medium | Security-critical logic could not be tested without importing external `pk_core`. | **FIXED.** Moved to dependency-free `runtime.py` with standalone regression suite. |
| A-10 | Medium | 100-item framework assessment language risked being interpreted as complete production certification despite absent runtime/integration artifacts. | **FIXED IN DOCUMENTATION.** README/changelog now distinguish checklist accounting from production evidence and link to the missing-components register. |
| A-11 | Low | Evidence references pointed at `component.py::Instance*` although implementation lived inline there and would move during hardening. | **FIXED.** Evidence references now identify `runtime.py`. |
| A-12 | Open production gap | Lexical checks cannot stop symlink/TOCTOU escapes if a host later opens the returned path by name. | **NOT IMPLEMENTABLE IN THIS REFERENCE MODEL.** Requires descriptor/handle-relative host adapter; tracked as MC-003. |

## Hardened invariants

- World authority is immutable after construction from the caller's perspective.
- No preopen can be added when filesystem authority is absent.
- Preopen policy cannot be mutated through the public mapping view.
- Authority retargeting is explicit, not an overwrite side effect.
- Absolute guest paths, traversal escapes, NUL paths, absent preopens, and absent capabilities fail closed.
- Root strings that would normalize to a different authority are rejected rather than silently corrected.
- Security-relevant reference-model operations are chained without requiring wall-clock access.
- Core security tests remain executable even when the external orchestration framework is unavailable.

## Validation performed on 4.2.0

The hardened package is validated with:

1. archive/path integrity checks;
2. `python -m compileall`;
3. dependency-free unit/security regression tests;
4. a dedicated optimized-mode (`python -O`) run of the dependency-free suite;
5. a controlled `pk_core` compatibility shim used only to exercise package imports/assessment glue when the real external framework is unavailable;
6. version-string consistency checks;
7. a clean re-archive and SHA-256 digest.

The final validation outputs are recorded in `VALIDATION.txt` in the hardened package.

## Residual risk / interpretation

Version 4.2.0 is suitable as a **hardened architecture/reference component**. It should not be described as a production WASI implementation until the runtime, WIT, descriptor-safe filesystem operations, real provider integrations, compatibility matrix, supply-chain controls, performance certification, telemetry, and operational controls in `MISSING_COMPONENTS.md` are implemented and evidenced.


---

# v4.3.0 addendum — checklist execution (2026-09-22)

**Input:** `inv13_system_interface_v4.2.0_hardened.zip` + `inv13_system_interface_v4.2.0_COMPONENT_CHECKLISTS.md` (MC-001..MC-032 plus program gates, 787 checkboxes).  
**Output:** 4.3.0 with a stdlib-only host layer, 124 automated tests (all passing under `python` and `python -O`; `test_component` skips without `pk_core`), and the evidence bundle in `evidence/`.

## Checklist accounting

| Mark | Count | Meaning |
|---|---|---|
| `[x]` | 330 | implemented and evidenced by an automated test/artifact in this package |
| `[~]` | 153 | partially implemented / evidenced; gap stated per component |
| `[ ]` | 304 | not evidenced |

No P0/P1 component is declared production-closed. P0 status: MC-003, 004, 005, 008, 009, 010, 011, 012 implemented at reference scope; MC-001, 002, 006, 007 partial.

## New findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| B-01 | Medium | Contract SLO "resolve p99 < 1 µs" is not met: measured lexical resolve p99 ≈ 50–60 µs (includes audit hashing) on a 2-vCPU x86-64 host; openat2 fd open p50 ≈ 4 µs. | **OPEN** — owner must choose a native fast path or revise the SLO. Regression ceilings in `BENCH_BASELINE.json` are not the SLO. |
| B-02 | High (in new code) | Fuzzing (`Fuzz.test_identity_tokens_mutation`) showed tokens with a mutated final base64 character still verified (non-canonical padding bits). | **FIXED** before release: canonical base64url enforced. |
| B-03 | Low | `__init__.py` imported `pk_core` unconditionally; the dependency-free runtime was only importable by file path. | **FIXED.** |
| B-04 | Info | 4.2.0 `resolve()` remains lexical; it is now paired with the descriptor-relative provider in `host/fs.py`, which is what the end-to-end host uses. | By design. |

## Environment limits of this pass
No Wasmtime / wasm-tools / wit-bindgen available (component-model and binding generation not executed); single platform (Linux x86-64, Python 3.11.15, Node 22.22.2); no organisational inputs (owners, KMS, PKI, observability stack). These are recorded as gaps, not papered over with mocks.
