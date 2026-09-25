# Changelog - GAP-05

## 4.3.0 - 2026-09-22

Applies the *GAP-05 v4.2.0 Missing Components - Professional Engineering Checklist v1.0.0*
(50 components, 1,516 items) by building and executing the components, not by ticking
boxes.  `model.py`, `contract.py`, `component.py`, `CHECKLIST.json`, `MISSING_COMPONENTS.md`
and `tests/test_model_logic.py` are byte-identical to 4.2.0; everything new is additive.

### Added - production layer (`production/`, 22 modules, stdlib + `cryptography`)

- Identity (SPIFFE-style Ed25519 workload credentials, channel-bound single-use handshake),
  signed write provenance, durable counter allocation with receive-side jump/equivocation
  guard, WAL with torn-tail vs corruption discrimination, checksummed atomic snapshots,
  tenant/environment namespaces, JSON-Schema wire schemas + strict validators + corpus,
  version negotiation, content-addressed op_id dedupe, signed hash-chained audit ledger with
  bounded segments and verified archive handoff, AES-256-GCM keyring with rotation/rewrap,
  default-deny authorization, CAS membership store with forward rollback, fencing and
  reseed-as-new-incarnation, GAP-13 resolution adapter (timeouts keep conflicts open,
  stale decisions refused), Merkle-leaf anti-entropy through the authenticated accept path,
  framed lossy-link transport with bounded windows, causal tombstones with acknowledged GC
  and resurrection floors, CRDT registry (read-time merge), quarantine operator API,
  immutable views, snapshot migration 1->2, backup/verify/restore with recovery-mode
  fencing, metrics/logs/health/admission/epoch expiry/analytics, sharded locks, batch
  apply, binary codec, read-only admin CLI, bounded model checker, benchmarks with
  PROPOSED gates, runbooks, pyproject/SBOM/compatibility matrix/CI script/checksums.
- `ReplicaNode` integrates all of it around the unchanged core `ReplicatedKey`.

### Evidence (see `evidence/`)

- 114 new tests (unit, property, deterministic fuzz 24k cases, real `os._exit` crash
  injection at 7 persistence boundaries x 3 cycles, 3-OS-process partition/restart run,
  4-process counter contention) - 114/114 pass; the 12 + 3 v4.2.0 tests still pass/skip.
- Model checker over the *real* core: 42,492 delivery orders / 335,556 states, 0 violations;
  it detects the reverted v4.2.0 overflow fix (mutation check).
- Checklist mapping of all 1,516 items: **0 ticked**. 186 LOCAL_VERIFIED_UNREVIEWED,
  412 DESIGN_RECORDED_UNREVIEWED, 10 MEASURED_UNDER_PROPOSED_TARGET, 404 PARTIAL,
  146 BLOCKED, 358 NOT_EVIDENCED. All 6 global gates and 10 certification items BLOCKED.
- The first mapping claimed 333 component-specific items locally verified.  An adversarial
  second pass (a separate model agent reading every cited test body; not a human reviewer)
  accepted 126 and demoted 191 to PARTIAL and 16 to NOT_EVIDENCED (`evidence/tag_review.json`).
  The shipped numbers are the demoted ones.

### Defects found by this pass's own tests and fixed

1. **WAL -> audit crash window**: a kill after the WAL fsync but before the audit append
   left a durable, recoverable write with no audit record.  Recovery now back-fills
   `apply_recovered` records; the regression test fails with the back-fill removed.
2. **Counter allocator was single-process**: two processes sharing a counter file raced on
   one temp filename (crash) and had no cross-process exclusion (possible counter reuse).
   Now an exclusive `flock` + durable ceiling re-read + per-process temp names; 4-process
   test: 200 allocations, 0 collisions.
3. **Encrypted WAL recovered without its key reported ready**: the undecryptable record was
   rejected but health stayed ready.  Readiness now fails while recovery rejected records.
4. **CRDT single-value read returned a non-canonical encoding** (`{"b": 2}` vs `{"b":2}`),
   so replicas could return different bytes for one logical value; `merge_all` now
   canonicalises.
5. **Benchmark miscounted the quarantine-flood acceptance ratio** (0.995 - the first write
   converges rather than conflicts); the gate reported a false miss.

### Findings that refute an expectation

- The binary codec's full round trip is **not** faster than canonical JSON (539 us vs
  547 us for a 16 KiB value): re-validation and the content hash dominate.  Only the lazy
  (no-materialise) decode is ~25x faster.  MC43-001 ("prove copy overhead is material")
  is therefore answered *no* for full decoding.

## 4.2.0 - 2026-09-22

Audit, correctness, hardening, and testability pass.

### Correctness fixes

- Fixed bounded-conflict convergence: more than `max_siblings` concurrent writes no longer leave an arrival-order-dependent active set. The full unresolved frontier is deterministically ranked; overflow is preserved in quarantine.
- Fixed quarantine causality: future writes are compared against both active siblings and quarantined writes, so a causally newer write can supersede an overflowed predecessor and a stale write cannot bypass a newer quarantined write.
- Fixed resolution coverage: `resolve()` now merges the version vectors of both active and quarantined writes before clearing the conflict, preventing overflow writes from reappearing as concurrent after a nominal resolution.
- Fixed convergence reporting for `max_siblings=1`: a single active sibling plus quarantined concurrent writes is no longer reported as converged.
- Added equal-vector equivocation detection. Reusing one causal vector for different write content raises `VectorEquivocationError` instead of manufacturing a conflict from an impossible/hostile duplicate event.

### Input and state hardening

- Added `InvalidWrite` and strict/canonical `Write` validation for key, site, value type, vector shape, duplicate vector sites, positive integer counters, and presence of the author's own counter.
- Added constructor validation for replica sets and `max_siblings`.
- Added explicit type checking at the `apply()` boundary.
- Canonicalized vectors and conflict-frontier ordering for reproducible state.
- Added in-process `RLock` protection around mutable state-machine operations.
- Preserved duplicate replay evidence without duplicating quarantined frontier entries.

### Architecture and testability

- Extracted the causal state machine into dependency-light `model.py`.
- Made package integration symbols lazy so the model can be imported/tested without `pk_core`.
- Added standalone tests covering malformed inputs, duplicates, equivocation, 120 delivery-order permutations, quarantine replay, causal replacement of quarantined writes, full-frontier resolution, and concurrent threaded application.
- Updated the conformance version pin to 4.2.0.

### Documentation/integrity

- Corrected README claims: the supplied archive does not contain the previously referenced `MASTER.md`.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.
- Security wording now distinguishes replica-membership validation from cryptographic authentication; declared-replica provenance remains a missing production component.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- Replaced bare behavioural `assert` usage with `_verify()` so checks survive `python -O`.
- Added explicit failure branches for expected-refusal checks.
- Added stdlib conformance test, version file, and `__version__`.

### Defects fixed

- Rejected writes addressed to a different key.
- Rejected duplicate vector sites, non-positive/non-integer counters, and missing author counters.
- Rejected conflict resolution authored by a non-replica.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
