# INV-05 Audit Report — 4.3.0 implementation pass

**Input:** `inv05_current_control_state_system_v4.2.0_hardened.zip` + *INV-05 v4.2.0 52-Component Professional Checklist* (52 components, 2 346 sub-items).
**Output version:** 4.3.0 · **Date:** 2026-09-22 · **Gate report tree digest:** `b167d57a3094cd80…` (see `evidence/gate_report.json`).

## Result in one paragraph

The 4.2.0 package was an in-memory reference model. 4.3.0 adds a working single-member control-state service that covers the checklist's engineering items: MVCC engine, durable encrypted WAL with crash recovery, watch streaming, leases with fencing, mTLS transport, authn/authz, namespaces, audit, observability, backup/restore, a replication contract, and the CI/traceability tooling that evidences it. The CI acceptance gate passes. The release gate still says **BLOCK**, and that is the correct answer: the remaining P0/P1 gaps need owner decisions (backend choice, MASTER.md, approvers, licence, signing identity) or artefacts that were not supplied (pk_core, dependency hashes, adjacent layers, production hardware).

## Verification (this run)

| Stage | Result |
|---|---|
| Unit + integration (normal) | 170/172 passed, 0 failed; the only skips are the 2 approved `pk_core` framework tests (EX-003) |
| Optimized runtime (`python -O`) | 172 run, 0 failed |
| Conformance vectors | 25/25 |
| Schema / error-catalog compatibility | no breaking changes |
| Traceability C001–C100 | consistent; blocked-external 1, partial 21, verified 76, verified-single-member 2 |
| MASTER.md reference policy | clean |
| Exceptions register | 9 open, none expired |
| Performance smoke | write p99 0.38 ms, 19727 ops/s (in-memory, sandbox) |
| Restore drill | state equal after encrypted backup → verify → restore |
| Release gate (single-member) | **BLOCK**: MC-002, MC-024, MC-027, MC-037, MC-040, MC-042, MC-048, MC-049 |

## Checklist status (all 2 346 sub-items, `traceability/CHECKLIST_STATUS.md`)

blocked-external: 101 · done: 1859 · done-single-member: 42 · open-approval: 221 · partial: 123

`done` means implemented **and** backed by an automated test or evidence file (checklist rule 1). Generic sub-items (scope, threat model, tests, telemetry, runbooks) point to the shared artefacts that satisfy them; every sub-item needing a human approval is `open-approval`, not `done`.

## Defects found and fixed while building 4.3.0

| Defect | Severity | Fix |
|---|---|---|
| Watch catch-up larger than the queue cancelled a new watch immediately, so a lagging client could never resume | High | Catch-up now pages from shared history; overflow falls back to history instead of dropping (ADR-006) |
| Lock-order inversion between watch polling (watch lock → store lock) and commit listeners (store lock → watch lock) | High (deadlock) | Single order store → watch everywhere; fill path restructured |
| A progress frame could report a revision whose events were still being offered (read without the store lock), making it an unsafe resume point | High (silent gap) | Progress reads the head under the store lock, and only in live mode with an empty queue |
| TLS handshake ran on the accept thread, so one slow client could stall all accepts | Medium | Handshake moved to the per-connection thread with a socket timeout |
| Replication batches could split one revision across batches | Medium | Batches end on revision boundaries |
| Follower snapshot resync was not persisted | Medium | `ReplicaApplier(durable=…)` checkpoints after resync |
| `Namespace` rejected the cluster-admin target used for compaction/metrics | Low | Added `security.CLUSTER` |

## Honest limits

* A single member has no consensus. HA, membership, partition behaviour and real backend integration are specified (`docs/CONSENSUS_CONTRACT.md`) but unproven (EX-001).
* Benchmarks come from a 2-vCPU sandbox, not target hardware (EX-005).
* Evidence is HMAC-signed only when `INV05_SIGNING_KEY` is set (EX-008), and `requirements.lock` has no hashes yet (EX-009), so the CI install step fails closed until they are added.
* Owner names, ADR approvals and the outbound licence are proposals (EX-006, EX-007).

---

# Previous report (4.2.0)

# INV-05 Audit Report

**Input:** `inv05_current_control_state_system.zip`  
**Input version:** 4.1.0  
**Hardened version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** archive integrity, Python correctness, reference-state semantics, concurrency, tests, documentation claims, and production-readiness evidence contained in this archive.

## Executive result

The archive was structurally valid and compiled, but its original standalone test posture was misleading: all three tests were skipped when `pk_core` was unavailable, producing an `OK (skipped=3)` result without exercising the state model. The reference compare-and-swap implementation also lacked a serialization primitive, so its compare phase and writes were not explicitly atomic across concurrent callers.

Version 4.2.0 separates the state model from the framework, adds a lock around compare/mutate/watch/compaction state access, fails closed on malformed keys/revisions, prevents direct mutation of internal state containers, adds always-runnable behavioral tests, corrects documentation/evidence claims, and records production gaps explicitly.

## Findings and dispositions

| Finding | Severity | Disposition in 4.2.0 |
|---|---|---|
| Full original test class skipped when `pk_core` was absent, allowing a zero-execution “OK” | High | **Fixed.** Metadata/reference-model tests always run; only framework checks skip explicitly. |
| CAS compare and mutation had no concurrency lock | High | **Fixed.** Transaction compare + all writes execute under one `RLock`. |
| Watch and compaction could race with writes without an explicit consistency boundary | High | **Fixed.** Read snapshots, watch, compact, and transaction mutation share the same lock. |
| Invalid compare revisions were not validated; keys accepted empty/NUL forms | Medium | **Fixed.** Strict non-negative integer revision checks and key validation added. |
| Public `data` / `history` containers exposed mutable internal structures | Medium | **Fixed.** Accessors now return container snapshots. |
| Core model could not be imported without `pk_core` because package initialization eagerly imported framework modules | Medium | **Fixed.** Framework exports are lazy; `state.py` is dependency-independent. |
| Evidence locations still pointed to `component.py::ControlState.*` after model extraction | Medium | **Fixed.** Evidence paths now target `state.py`. |
| README stated `MASTER.md` was carried in the archive although it was absent | Medium | **Fixed as documentation integrity.** Claim removed; missing artifact is tracked as MC-002. |
| README could be read as production-store readiness despite only containing an in-memory model | Medium | **Fixed as scope integrity.** Reference-model limitation and residual production gaps are explicit. |
| Full 100-item framework gate could not be independently rerun from this archive | High | **Open / external dependency.** Requires `pk_core`; tracked as MC-001. |

## Verification performed

### Archive and static integrity

- Original ZIP CRC/integrity test: **PASS**.
- Path traversal / absolute-path / ZIP symlink scan: **PASS**; no unsafe entries found.
- Python compilation after hardening: **PASS**.
- `CHECKLIST.json`: **PASS** for declared count=100, unique IDs, contiguous ordinals/IDs, ten dimensions, and non-empty requirements.
- Production-source bare-`assert` scan: **PASS**; no bare asserts in non-test Python files.

### Test results after hardening

Normal Python:

```text
Ran 10 tests
OK (skipped=2)
```

Optimized Python (`python -O`):

```text
Ran 10 tests
OK (skipped=2)
```

The eight non-framework tests execute in both modes. The two skipped tests are the explicitly framework-bound 100-item assessment and optimized framework assessment because `pk_core` is not bundled.

Behavioral coverage added includes:

- compare-and-swap mismatch performs no write;
- 16 concurrent contenders using one expected revision produce exactly one winner;
- compaction refuses stale watches without silent gaps;
- invalid revisions/keys fail closed;
- compaction cannot advance beyond the current revision;
- snapshots returned from `data` and `history` cannot mutate internal containers;
- package version/reference model can be imported without the external framework.

## Versioning decision

The version was bumped **4.1.0 → 4.2.0** rather than a patch release because the package gained a new standalone `state.py` API surface, lazy framework loading, stricter input validation, and defined concurrency behavior while retaining the existing component-facing semantics.

## Residual limitations

This audit does **not** certify a distributed production service. The package still lacks the backend, persistence, consensus integration, network schemas/server, identity/authorization, durability/DR, observability, production performance evidence, integration/chaos/security test suites, and release/supply-chain controls enumerated in `MISSING_COMPONENTS.md`.

The full `pk_core` 100-requirement gate was not executed because that dependency is absent from the supplied archive; no replacement/stub was fabricated, because doing so would create false evidence.
