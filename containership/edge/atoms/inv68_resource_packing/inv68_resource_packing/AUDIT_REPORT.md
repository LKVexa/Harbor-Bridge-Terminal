# INV-68 audit, fix, hardening, and version-bump report

**Input version:** 4.1.0  
**Output version:** 4.2.0  
**Audit date:** 2026-09-22

## Executive result

The repository was parsed, audited, modified, hardened, version bumped, compiled,
and re-tested. The core resource-packing implementation is now independently
importable and testable without `pk_core`, validates hostile/malformed numeric
inputs, preserves caller data, provides deterministic decision evidence, and
ships versioned interface schemas and fixtures.

The post-update repository is **not** independently production-complete. A second
100-item evidence audit found **12 implemented**, **21 partial**, and **67 missing**
requirements when judged only by concrete files/behavior in this archive.
`MISSING_COMPONENTS.md` groups those remaining requirements into 42 actionable
components (40 checklist-derived plus 2 supplementary repository gaps).

## Baseline audit findings (4.1.0)

### High-impact defects / integrity problems

1. **Framework coupling prevented standalone use.** Importing the package eagerly
   imported `component.py`/`contract.py`, so absence of external `pk_core` made
   the package unusable even for the pure packing functions.
2. **Conformance suite could appear green by skipping everything.** All three
   original tests were inside a `skipIf(pk_core is None)` class. In this supplied
   environment the result was `OK (skipped=3)`, meaning even version consistency
   was never tested.
3. **Caller workloads were mutated.** `pack()` added a `host` key directly to
   caller dictionaries, creating hidden cross-call state and violating clean
   interface expectations.
4. **Non-finite and structurally malformed requests were insufficiently guarded.**
   NaN/infinity, booleans-as-numbers, missing fields, invalid names, and duplicate
   identities could produce ambiguous or unsafe behavior rather than precise
   validation errors.
5. **Fragmentation trusted impossible host state.** It could report negative
   stranded capacity instead of failing on an over-limit accounting invariant.
6. **Placement and lower-bound normalization were not fully aligned.** Sorting
   used raw host capacity while lower-bound logic used overcommit/headroom-adjusted
   capacity; 4.2.0 uses effective capacity consistently.
7. **No machine-readable decision explanation.** The API returned hosts/unplaced
   names only; it did not identify why a placement opened a host or why a request
   was refused.
8. **Typed schema evidence was missing.** The checklist requires versioned typed
   external contracts, but the archive contained no schema files.
9. **README provenance error.** It asserted that `MASTER.md` was included, but the
   archive had no `MASTER.md` member.
10. **The prior 100/100 gate claim was not reproducible from the supplied archive.**
    `pk_core` was not present, and many production checklist requirements had no
    repository-local artifacts/evidence.

### Archive integrity checks

- ZIP path traversal check: no absolute paths or `..` members found.
- Baseline Python bytecode compilation: passed.
- Baseline tests: three tests discovered, all three skipped because `pk_core` was unavailable.

## Changes applied in 4.2.0

### Engine architecture

- Added dependency-free `packing.py`.
- Made `pk_core` integration lazy from `__init__.py`.
- Kept the legacy `pack(...) -> (hosts, unplaced)` shape.
- Added `pack_detailed()` returning `PackingResult` and `PlacementDecision`.

### Validation / safety

- Strict finite real validation for host CPU/memory, headroom, workload CPU/memory,
  and host accounting.
- Rejects bool values as resource numbers.
- Rejects missing required fields and empty workload names.
- Rejects duplicate workload identities.
- No caller-input mutation.
- Validates fragmentation invariants and fails closed on impossible host accounting.
- Deterministic equal-share ordering.
- Effective-capacity policy shared by sort, placement, and lower-bound calculation.

### Contract / interface evidence

- Added JSON Schema 2020-12 files for `PK_PACK/1` request/response,
  `PK_PACK_CAPACITY/1`, and `PK_PACK_FRAG/1`.
- Updated `contract.py` interface descriptions to reference schema files.
- Added request and response examples.

### Tests

- Added standalone engine/hardening tests that run without `pk_core`.
- Kept framework-dependent 100-item/optimized-mode checks isolated to the actual
  framework integration tests.
- Added optimized-mode smoke coverage for the pure engine.

### Documentation / versioning

- Bumped `VERSION` and `__version__` to 4.2.0.
- Updated README and changelog.
- Corrected the false `MASTER.md` presence claim.
- Added this audit report, the 100-item post-update audit matrix, and complete
  missing-component inventory.

## Verification performed on 4.2.0

Commands executed from the package parent:

```text
python -m compileall -q inv68_resource_packing
python -m unittest discover -s inv68_resource_packing/tests -v
PYTHONPATH=<package-parent> python -O <pure-engine smoke>
```

At the point of this report, the standalone suite passes; the two tests requiring
`pk_core` are skipped because that external dependency is not present in the
supplied archive/environment. The final packaged ZIP is re-verified after report
creation and its digest is emitted alongside the artifact.

## Post-update gap conclusion

The algorithm/library layer is substantially hardened, but a production control
plane still needs the governance, security, configuration lifecycle, resilience,
observability, compatibility, performance certification, release evidence, and
operations components enumerated in `MISSING_COMPONENTS.md`.

---

# 4.3.0 — missing-component implementation pass (2026-09-23)

**Governing prompt/workflow:** `source/INV68_v4.2.0_Missing_Component_Implementation_Checklists.md`
(sha256 `7dfbfa2f…a7daafa`; 42 components, 1,844 checklist items).
**Baseline:** the supplied `inv68_resource_packing_v4.2.0_hardened.zip`
(sha256 `94eb06b1…ef35`), git commit `b1ec149`.
**Executed checklist:** `source/INV68_v4.2.0_Missing_Component_Implementation_Checklists.executed.md`.

## Defects found in 4.2.0 by this pass (all fixed, all with regression tests)

1. **Latency SLO violated by ~3×.** 1000 workloads: p50 311 ms (SLO p99 < 100 ms);
   5000 one-per-host workloads: 51 s. Cause: re-validation of each workload for every
   candidate host and full hosts never leaving the scan. 4.3.0: ~6 ms and ~45 ms with
   byte-identical decisions (differential test over 300 batches + fuzz oracle).
2. **`lower_bound` raised `OverflowError`** on extreme finite inputs (fuzz finding).
3. **`lower_bound` counted unplaceable workloads**, overstating the bound and flattering
   efficiency whenever work was unplaced (fuzz oracle finding; `placeable_only=True`).
4. **Service layer (new code) caught by its own fuzzing before release:** `1e999` JSON
   numbers produced an internal error instead of `INVALID_REQUEST`.

## Result

| Measure | 4.2.0 | 4.3.0 |
|---|---|---|
| Missing components complete | 0 / 42 | **0 / 42** — COMPLETE needs reviewer sign-off; none exists |
| Components implemented locally | — | 24 IMPLEMENTED_LOCAL · 10 PARTIAL · 2 BLOCKED_EXTERNAL · 6 GOVERNANCE_PENDING |
| Checklist items (1,844) | 0 done | see `evidence/ITEM_LEDGER.json` counts (DONE / PARTIAL / OPEN_EXTERNAL / OPEN_GOVERNANCE) |
| INV-68-C### controls | 12 implemented · 21 partial · 67 missing | **73 verified · 27 partial · 0 missing** (`REQUIREMENTS_MATRIX.json`) |
| Standalone tests | 25 (+2 pk_core skipped) | 77 pass (+2 pk_core skipped), normal and `-O` |
| Exit gate | none | **NO_GO** (`evidence/EXIT_GATE.json`) |

**How to read the item counts.** Items were classified per checklist subsection
against the code, then downgraded (never upgraded) by keyword rules for governance and
external dependencies, and withheld from DONE when their evidence file was missing or
failing. Five seeded random samples (275 DONE items) were read against the code; about
55 overclaims were found and corrected (by fixing code/docs where cheap, otherwise by
item overrides). The last sample still needed ~10/50 corrections before the final batch,
so **treat DONE as an upper bound** with an estimated 10–20 % residual that a reviewer
would mark PARTIAL. The component statuses and control matrix were set by hand and are
the more reliable summary.

## Evidence produced (all in `evidence/`, digests in the exit gate)

TESTS / TESTS_O (unit, normal and `-O`) · SCHEMAS (examples + live documents, jsonschema
2020-12) · FUZZ (3,000 engine + 3,000 service + config + auth cases, 0 findings after
fixes) · FAULTS (14 scenarios) · STRESS (7 races incl. 6-process activation race) · SOAK
(60 s release run; certification needs ≥ 1 h) · PERF + PERF_GATE · INTEGRATION (9
emulated neighbour paths) · INTEGRATION_REAL (FAIL: nothing real to integrate with) ·
SECRET_SCAN · SOURCE_CHECK (FAIL: MASTER.md unverified) · PREFLIGHT / PREFLIGHT_CERT ·
ROLLBACK_DRILL · EMERGENCY_DISABLE · BACKUP_RESTORE · ALERTS · SLO (FAIL: lab only) ·
BUILD · INSTALL (fresh venv) · RELEASE_VERIFY (FAIL: license, ephemeral signer, lock
hashes) · GOVERNANCE (FAIL: no named people) · ITEM_LEDGER · REQUIREMENTS_MATRIX · RUN ·
EXIT_GATE.

## What closes NO_GO (nothing below can be done from code alone)

| Blocker | Needs |
|---|---|
| pk_core conformance (MC-02; 2 skipped tests, PREFLIGHT_CERT, INTEGRATION_REAL) | the pk_core package/revision + `PK_GATE_RESULTS.json` for INV-68 |
| MASTER.md provenance (MC-01) | the authoritative series source bytes |
| real adjacent components (MC-08, MC-29) | INV-67, SCH-01, GAP-10, INV-72 implementations |
| platforms (MC-29, MC-41) | running the defined CI matrix (Windows/macOS, 3.10–3.13) |
| supply chain (MC-09, MC-42) | managed signing key, hashed dependency lock, chosen license |
| production evidence (MC-24, MC-33, MC-23 E, MC-31) | live SLIs, edge hardware, ≥ 1 h soak |
| governance (MC-03, MC-04, MC-13, MC-36, MC-38, MC-39) | named owners/on-call, ADR approval, threat-model review, security intake, first review round |
| release approval | a human approval record (not a service identity, not the policy administrator) |

## Donor parts

`redaction.py`, `audit.py`, `provenance.py` and the `release_gate.py` structure were
adapted from the owner's INV-64 4.3.0 release (itself from INV-44 4.3.0), same copyright
holder; see THIRD-PARTY-NOTICES.md. No third-party code is bundled.
