# PLN-05 Elasticity Plane — Post-Remediation Audit Report

**Audited version:** 4.2.0
**Audit date:** 2026-09-23
**Governing workflow:** `source/PLN05_v4.1.1_Missing_Component_Remediation_Checklists.md` (34 components MC-01..MC-34, 1 468 checkboxes; sha256 in `source/SOURCE.json`)
**Evidence:** `evidence/4.2.0/` (release tier) — `manifest.json`, `EXIT_GATE.json`, `MC_STATUS.json`, `CHECKLIST_EXECUTED.md`, logs, bench/soak/fault results, wheel/sdist/SBOM/provenance.

## Executive result

- **Exit gate: NO_GO** (release tier). The blockers are the ones this repository cannot clear by itself: owner decisions and external dependencies. They are listed below. No blocker comes from a failing behavioural test.
- **Checklist coverage C001–C100 (4.1.1 → 4.2.0):** before, 13 present, 25 partial and 62 missing. Now:

  | Status | Count |
  |---|---|
  | verified | 73 |
  | partial | 14 |
  | governance-pending | 6 |
  | implemented, not independently verified | 3 |
  | blocked-external | 2 |
  | waiver-proposed | 2 |

  No row was marked verified without an executable check that resolves (`tools/traceability.py`).
- **Remediation items (1 438 component boxes):**

  | Status | Count |
  |---|---|
  | DONE | 1 200 |
  | PARTIAL | 114 |
  | OPEN_EXTERNAL | 43 |
  | OPEN_GOVERNANCE | 81 |

  The 30 remaining boxes are the global and final-closure gates, which `tools/gate.py` evaluates.
- **Components:**

  | Status | Count |
  |---|---|
  | IMPLEMENTED_LOCAL (every Definition-of-Done item met locally; closure needs owner sign-off) | 19 |
  | PARTIAL | 10 |
  | GOVERNANCE_PENDING | 4 |
  | BLOCKED_EXTERNAL | 1 |
  | COMPLETE | 0 |

  No component can be COMPLETE without the owner's closure approval.

## Verification performed (CPython 3.11.15, Linux x86_64, cloud container)

Every tier passed in both the presubmit and release runs except two. The framework-conformance tier's 2 `pk_core` checks were skipped, which the release tier counts as FAIL. The performance gate failed at release tier because the baseline is PROPOSED rather than APPROVED.

| Tier | Result |
|---|---|
| unit + plane + ops + repository | 122 tests, normal and `-O` |
| contract fixtures | 14 valid, 64 invalid, 8 sequences, run through the real boundary |
| adversarial security | 20 tests, one per threat T01–T20, normal and `-O` |
| fault harness | FS01–FS19, all invariants asserted |
| fuzz/property | 20 000 mutated payloads, long random controller sequences, config and state-file fuzz |
| multi-instance fuzz | 400 seeds × 300 steps: two instances on shared state, with clock jumps, outages, restarts, freezes and resumes |
| concurrency | 8 reporters + reader + controller threads; leader contention |
| compatibility | schema-evolution checker, state migration, version negotiation |
| soak | 200 000 decisions; memory growth after warm-up 0.06 %; no queue backlog; no latency drift; 0 errors |
| burst | 5 000 offered; rejected with recovery |
| fleet | 10 000 persisted scopes in one process at ≈ 500 decisions/s with fsync; not fleet certification |
| benchmarks | p50 0.13 ms; p95 0.17–0.21 ms; p99 0.26–0.34 ms; 7 050–7 400 decisions/s (two release runs; `evidence/4.2.0/bench.json` is the recorded one); cold start p50 0.8 ms; persisted p95 1.35 ms; peak 34 MB per 10 k decisions |
| packaging | wheel and sdist rebuilt byte-identical; clean-venv install, uninstall, reinstall; 4.1.1 → 4.2.0 → 4.1.1 rollback drill |

## Defects found and fixed during this pass

**Found by the pass's own tests (6):**
- a FIFO reordering race;
- `submit_demand` returning another caller's decision;
- a raw `OSError` leaving memory ahead of disk on the decision path;
- unbounded in-memory audit and consumer history (the soak leak detector found this);
- `..` accepted in state scope segments;
- two confounded test fixtures.

**Found by the independent adversarial review:** a separate agent attacked the build without reading the tests. Its findings were reproduced, fixed, and turned into regression tests (`tests/test_plane.py::ReviewFindingsTest`, `tests/fuzz/test_multi_instance.py`).

1. **Critical: stale leader on shared state.** A controller whose lease had lapsed re-acquired it and decided from cached memory. It published a target above the newer envelope and overwrote that envelope on disk. The fix: a new lease term now reloads the scope from shared state, and every writer must hold the lease.
2. Authority changes were not transactional when persistence failed.
3. Site scope was not enforced on explain/status and on tenant-wide controls.
4. Resume proposals never expired and were not bound to the controls they would release.
5. Authority expansion was accepted during a time fault. Also minor bounds issues.
6. A lowered ceiling was not published until the next demand sample.

**Found while porting the reviewer's fuzzer:**

7. Two holds at the same instant produced the same `decision_id`, so the consumer silently dropped the second.
8. A lapsed lease looked valid again after a wall-clock step backwards.

The independent review also judged 9 traceability citations weak. Eight were re-pointed to behavioural tests, with new tests added where none existed. The ninth, C066, stays a document-only row under the proposed waiver W-002.

## Critical architectural inconsistency (4.1.1) — status

It is resolved in form but not in authority. `docs/adr/ADR-0001-pln05-authoritative-scope.md` chooses the capacity-controller interpretation. It attributes snapshot/restore to INV-26, microfunctions to INV-31 and reassignment to SCH-01. Scope drift is now checked mechanically. The ADR is **PROPOSED**: the architecture owner must accept it, or choose alternative A, before MC-01 and C010/C011 can close.

## Remaining blockers (from `evidence/4.2.0/EXIT_GATE.json`)

**Owner decisions:**
- accept ADR-0001;
- assign the 8 ownership roles in `ops/oncall.json`;
- choose a license (`LICENSE-PENDING.md`);
- approve the performance baseline on a declared reference environment;
- approve or reject waivers W-001 (edge power/thermal) and W-002 (zero-copy);
- sign the release as `pln05.release-approver` and `pln05.service-owner` in `governance/approvals.json`.

**External:**
- `pk_core>=4.0,<5.0` and the sibling packages GAP-09, INV-26 and SCH-01. The framework-conformance tier and the real adjacent-layer integration tests are blocked on these.
- KMS/HSM keys and volume encryption at rest.
- Transport adapters (the TLS policy is enforced at their seam).
- CI running on a forge across the declared OS × Python matrix. The workflows are written; the action pins need verifying.
- A managed signing identity. Release signatures are ephemeral HMAC.
- Fleet-scale reference infrastructure.
- Power/thermal instrumentation.

**Named partials:** see `MC_STATUS.json` notes, for example:
- missing gauges for queue/breaker/lease;
- one span per decision;
- deadlines not enforced by the library (it has no network code);
- no rate limiter;
- incomplete wrong-type fixtures for the target schema;
- the soak runs at presubmit/release length (200 k decisions), not a long-duration certification.

## Release conclusion

4.2.0 turns the hardened 4.1.1 controller into an operable, tested, evidence-producing component:
- typed interfaces, IAM, configuration, durable state with leader fencing;
- emergency controls, observability and explain;
- resilience and security suites;
- reproducible packaging and a mechanical exit gate that refuses self-approval and skipped checks.

It is **not** production-certified. The gate's NO_GO is correct and should stay until the owner decisions and external dependencies listed above are supplied.
