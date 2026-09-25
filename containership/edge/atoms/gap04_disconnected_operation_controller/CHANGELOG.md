# Changelog — GAP-04

## 4.3.0 — 2026-09-22

Implementation pass against *GAP-04 v4.2.0 Missing Components — Professional Engineering Checklist v1.0.0* (56 components, 1,456 controls). Status per control: `evidence/CHECKLIST_STATUS.json`.

### Added (runtime)
- Signed, scoped, expiring autonomy leases (Ed25519, canonical JSON), trust bundles with purpose-bound keys, signed policy bundles with rollback floor, authority-epoch watermark and lease replay protection.
- Trusted clock with persisted anti-rollback high-water mark; reboot without a trusted anchor fails closed.
- Durable WAL: CRC + hash chain + HMAC, AES-256-GCM frames, fsync'ed single-frame transactions, torn-tail recovery, verifiable export, anchored compaction with archive, reserved capacity and deterministic storage freeze.
- Ownership lock + generation fencing; persisted partition epoch; idempotent decision ids bound to request hashes; deterministic reconciliation transactions with batch acks, compensation and quarantine outcomes.
- Adapters and contracts for GAP-01, GAP-05, GAP-12 (signed heartbeats, hysteresis, flap detection), GAP-13, PLN-07; mTLS SPIFFE authorization; machine-readable error model.
- Declarative configuration with atomic activation/rollback; configurable tier schedule; two-person, time-bounded overrides; quarantine with signed release; health/readiness/metrics endpoint; structured redacted logs; W3C trace propagation; admission control, retry budgets, circuit breakers; backup/restore/migration; staged rollout logic; SBOM/provenance/signing/verification; capacity calculator; production exit gate.

### Defects found and fixed during this pass (by the new suites)
- Full-state-per-decision frames made storage O(n²) and overflowed the frame bound → snapshot + delta frames (ADR-003).
- `decide()` deep-copied the whole decision log per call (latency grew 1 → 14 ms by 3k decisions) → O(1) undo; regression test added.
- Torn-write crash injection wrote partial frames mid-file (harness bug) and a crash between reconcile-complete and compaction left compaction undone → staged torn write fixed; compaction resumes at open.
- Reachability started as `down`, so a restarting node spuriously entered partition → new `unknown` state.
- Same-version policy with different content, and epoch-0 leases, were accepted → rejected.
- Enriched reconciliation record violated the v1 decision schema → versioned `PK_RECONCILIATION_RECORD/2`.

### Compatibility
- 4.2.0 public API of `AutonomyController` unchanged; new keyword fields are optional. 4.2.0 had no durable state, so upgrades start clean.

## 4.2.0 — 2026-09-22

Audit, correctness, lifecycle, and hardening pass.

### Correctness fixes

- Fixed the ineffective backdated-renewal check: validation now occurs before mutating `granted_at`.
- Renewal can no longer erase/bypass an active partition or unreconciled decision journal.
- Added `reconnect()` to perform reconciliation before renewal in one safe lifecycle operation.
- Local autonomy decisions are now rejected unless a partition is active.
- Backdated state-changing lifecycle operations are rejected.
- Reconciliation no longer accepts a timestamp older than the most recent state-changing event.

### Fail-closed hardening

- Enforced finite cached-policy staleness via `max_policy_staleness_ticks` / `PolicyStale`.
- Added bounded decision-journal capacity via `max_decisions` / `DecisionJournalFull`.
- Added constructor and timestamp validation.
- Added `RLock` protection for in-process shared state.
- Exposed pending decisions only through defensive deep copies.
- Added partition epochs, decision sequence numbers, lease bounds, policy age, and reason to decision evidence.
- Added safe connected-only cached-policy refresh.

### Architecture and verification

- Moved the dependency-free state machine into `controller.py`.
- Made `pk_core` contract/conformance imports lazy at package level.
- Added dependency-free unit tests and retained optimized-mode safety.
- Added JSON schemas for `PK_AUTONOMY_LEASE/1`, `PK_DEGRADATION_TIER/1`, and `PK_RECONCILIATION_RECORD/1`.
- Added `AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`, and an integrity manifest.
- Corrected README claims about production readiness and the absent `MASTER.md` file.
- Changed the conformance test to require all 100 checklist items to be assessed, not to treat that alone as independent proof that all production capabilities exist.

## 4.1.0 — 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- Replaced runtime bare `assert` checks with `_verify()` so behavioral checks survive `python -O`.
- Added explicit failure when expected refusal exceptions are not raised.
- Added stdlib conformance tests and VERSION metadata.

### Defects fixed

- Rejected backdated decisions that could otherwise regain a wider tier.
- Reported times before the lease grant as expired.
- Intended to reject backdated renewal (the implementation order was still defective and is corrected in 4.2.0).
- Rejected empty decision kind/subject.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
