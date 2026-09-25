# GAP-05 v4.2.0 Audit Report

Date: 2026-09-22  
Input version: 4.1.0  
Output version: 4.2.0

## Scope

Reviewed package structure, state-machine semantics, version-vector validation, conflict bounding, quarantine behavior, resolution, replay behavior, thread safety, documentation claims, and available tests. `pk_core` was not present in the supplied archive/environment, so integration tests that require it are retained but cannot be fully executed here; standalone core tests were added to remove that blind spot for state-machine logic.

## High-severity findings fixed

1. **Arrival-order-dependent overflow convergence.** With more concurrent writes than `max_siblings`, v4.1.0 retained the first arrivals and quarantined later arrivals. Different delivery orders therefore produced different active conflict sets from the same write set. v4.2.0 deterministically ranks the complete unresolved frontier.
2. **Quarantined writes were excluded from future causal comparison.** A stale or successor write could be judged only against active siblings. v4.2.0 treats active and quarantined writes as one unresolved causal frontier.
3. **Resolution ignored quarantined writes.** v4.1.0 resolved only active siblings, leaving overflow writes causally uncovered. v4.2.0 merges every unresolved vector before creating the resolving write and clears quarantine only after recording resolution.
4. **False convergence with `max_siblings=1`.** v4.1.0 defined convergence only by active sibling count. v4.2.0 includes quarantine in convergence state.

## Medium-severity findings fixed

- Malformed vector structure could fail with incidental `IndexError`/`TypeError` instead of schema-level rejection.
- Equal vector/different content was accepted as a conflict rather than flagged as equivocation/corruption.
- Replica-set and `max_siblings` constructor invariants were not enforced.
- State transitions were not atomic across threads.
- Quarantined replay could accumulate duplicate quarantine records.
- The core algorithm could not be imported/tested without `pk_core`.
- README claimed `MASTER.md` was present, but the supplied archive did not contain it.

## Security finding clarified

Membership validation only proves that a site identifier is in the configured replica set. It does **not** authenticate that the caller actually controls that replica, nor does it prove that the claimed counter/vector was legitimately allocated. v4.2.0 stops describing this check as sufficient protection against a forged vector. Cryptographic identity/provenance and trusted counter allocation remain P0 production gaps.

## Verification performed

- Python bytecode compilation of the package.
- 12 standalone standard-library unit tests for the model (also repeated under `python -O`).
- Exhaustive delivery-order check across all 120 permutations of five mutually concurrent writes with a three-sibling bound.
- Threaded application test across 20 concurrent writers.
- Existing 3-test `pk_core` integration/conformance suite retained with version pin updated to 4.2.0; all three skip when `pk_core` is unavailable.

## Residual risk

This is still an in-memory reference model rather than a production distributed replication service. Durable state, authenticated provenance, trusted counter allocation, tenant isolation, wire schemas, transport, encryption, telemetry, migrations, anti-entropy, delete/tombstone semantics, and fleet-scale operations remain outside the implementation. See `MISSING_COMPONENTS.md`.


---

# GAP-05 v4.3.0 Build Report (checklist application)

Date: 2026-09-22 - Input 4.2.0 - Output 4.3.0

**Method.** Each of the 50 components was built as code under `production/`, integrated in
`ReplicaNode`, and exercised by tests whose docstrings name the checklist items they
evidence.  `evidence/run_evidence.py` runs everything and assigns every item a status by
rule; a relevance floor downgrades any tag whose test shares no content word with the item
(50 component-specific items were downgraded to PARTIAL by it - under-reporting on purpose).

**Result.** 114/114 new tests pass; legacy suites unchanged (12 pass, 3 skip without
`pk_core`).  Model checker: 0 violations across 42,492 orders.  Items: 0 ticked; 186 locally
verified (126 component-specific after an adversarial second pass demoted 207 of the first
333 claims); 412 design-recorded (unreviewed); 10 measured under proposed targets; 404
partial; 146 blocked; 358 not evidenced.  Gates 001-006 and CERT-001-010: BLOCKED.

**Residual risk (unchanged in kind, reduced in scope).** No real mTLS/SPIRE, no KMS/HSM,
no signed release or provenance, no second-language validator, no multi-hour soak, no TLC
run, no UI, no appointed owners/reviewers, `pk_core` conformance still unexecuted, and
`MASTER.md` unrecovered.  See `CHANGELOG.md` for the five defects this pass found and fixed.
