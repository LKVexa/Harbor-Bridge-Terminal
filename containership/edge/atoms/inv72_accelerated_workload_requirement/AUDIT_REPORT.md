> **Historical (v4.2.0 audit).** The v4.3.0 result is in `POST_REMEDIATION_AUDIT.md`.

# INV-72 Repository Audit Report

**Repository:** `inv72_accelerated_workload_requirement`  
**Source version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** parse, correctness audit, security hardening, test hardening, version bump, and post-update missing-component audit.

## Executive summary

The source archive was syntactically valid but its strongest conformance claim
was not independently verifiable from the supplied files. The repository's only
three tests were all skipped when the external `pk_core` framework was absent,
which allowed an `OK (skipped=3)` result to look like a successful gate. The
README also claimed that `MASTER.md` was included even though the file was absent.

The update moves accelerator matching into a dependency-free module, adds strict
fail-closed validation, makes selection deterministic, adds atomic/no-reservation
matching modes, keeps package metadata importable without `pk_core`, and expands
repository-local verification. Version 4.2.0 passes both normal and optimized
local test runs. The unavailable `pk_core` integration tests remain explicitly
skipped rather than being counted as proof.

The post-update checklist audit is conservative and evidence-based: **9 of 100
requirements have concrete local evidence, 24 are partial, 65 are missing, and 2
are externally unverified**. `MISSING_COMPONENTS.md` lists every incomplete item;
`AUDIT_STATUS.json` contains the same 100-item result in machine-readable form.

## Source audit findings

### Correctness and security defects fixed

1. **Isolation fail-open:** any isolation value other than literal `dedicated`
   was effectively permitted to use a partition. Version 4.2.0 accepts only
   `dedicated` or `shared`; omitted isolation defaults to `dedicated`.
2. **Unsafe numeric acceptance:** Python booleans were accepted as integers and
   memory values such as `NaN` could enter matching logic. Version 4.2.0 rejects
   booleans-as-numbers, non-finite values, negative memory, and overflow values.
3. **Weak inventory validation:** duplicate device IDs and malformed/mutated
   device records were not rejected. They now fail with an explicit
   `InventoryValidationError`.
4. **Caller-order-dependent selection:** eligible devices were selected in input
   order. Selection is now deterministic using node/link/device ordering.
5. **Matcher coupled to integration framework:** importing the package pulled in
   `pk_core` before the pure matching logic could be used. The matcher and stable
   metadata are now dependency-free; component/contract loading is lazy.
6. **No side-effect-free eligibility API:** matching always reserved selected
   devices. `reserve=False` now performs eligibility checks without mutation;
   the default remains backward-compatible.
7. **Stale evidence pointer:** component findings referred to
   `component.py::match`; matching now correctly points to `matcher.py::match`.
8. **Interface documentation drift:** the documented request omitted the required
   tenant field and described a separate partition interface not implemented by
   the code. Runtime interface documentation now matches the actual request,
   inventory, and match surfaces.

### Verification defects fixed

1. **False-green local test behavior:** the source placed all tests under a
   class-level `pk_core` skip, so no repository-local assertion executed without
   that dependency. Version and pure-matcher tests now run independently.
2. **Insufficient deterministic/security coverage:** standalone tests now cover
   strict memory/class matching, interconnect grouping, isolation defaults,
   cross-tenant rejection, malformed values, duplicate inventory IDs,
   deterministic ordering, mutation atomicity, and side-effect-free matching.
3. **No repository integrity checks:** tests now verify the 100-item checklist
   sequence, synchronized version declarations, the corrected README reference,
   and absence of optimizer-sensitive bare asserts in runtime modules.
4. **Broken documentation claim:** the README's statement that `MASTER.md` was
   included was removed rather than fabricating an absent source artifact.

## Files added

- `matcher.py` — dependency-free hardened matcher and validation errors.
- `metadata.py` — stable element metadata without `pk_core` imports.
- `tests/test_matcher.py` — standalone security/correctness unit tests.
- `tests/test_repository_integrity.py` — repository consistency tests.
- `DEPENDENCIES.md` — explicit external dependency and adjacency limitations.
- `AUDIT_STATUS.json` — 100-item machine-readable post-audit status.
- `MISSING_COMPONENTS.md` — exhaustive incomplete-component report.
- `AUDIT_REPORT.md` — this audit record.

## Files changed

- `VERSION` and `__init__.py` — bumped from 4.1.0 to 4.2.0; lazy integration loading.
- `component.py` — uses hardened matcher and corrected evidence reference.
- `contract.py` — imports stable metadata and corrects interface descriptions.
- `tests/test_component.py` — local tests no longer disappear with `pk_core`.
- `README.md` — corrected artifact claims, runtime semantics, verification limits,
  and distinction between local verification and external integration gating.
- `CHANGELOG.md` — records the 4.2.0 audit/hardening pass.

## Verification performed

The following completed successfully against the updated repository:

```text
python -m compileall -q .
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
```

Result for each unittest run:

```text
Ran 23 tests
OK (skipped=2)
```

The two skips are the same external `pk_core` integration checks. **21 tests
execute and pass locally in normal mode and 21 execute and pass under `python -O`.**

## External verification not performed

The archive does not contain `pk_core`, a package/dependency manifest, a compatible
version constraint, or generated `pk_core` evidence. Therefore this audit does
not claim successful execution of:

```text
python -m pk_core run INV-72 ...
python -m pk_core gate INV-72 ...
python -m pk_core verify ...
```

It also does not claim integration with GAP-02, GAP-11, INV-68, or INV-69 because
those adjacent implementations were not part of the supplied archive.

## Post-update missing-component result

| Classification | Count |
|---|---:|
| Implemented locally | 9 |
| Partial | 24 |
| Missing | 65 |
| Unverified external | 2 |
| **Total** | **100** |

See `MISSING_COMPONENTS.md` for every partial/missing/unverified checklist item
and repository-level missing artifacts. See `AUDIT_STATUS.json` for the complete
machine-readable status of all 100 checks.

## Release assessment

Version 4.2.0 is materially safer and more testable than the supplied 4.1.0
archive, and its repository-local matcher checks are green. It is **not a
self-contained production-certified release** because the external integration
framework, adjacent-layer integrations, schemas, production configuration,
security/observability/resilience/performance programs, release automation, and
machine-readable acceptance evidence remain incomplete or absent as catalogued
in `MISSING_COMPONENTS.md`.
