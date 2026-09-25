# INV-72 post-remediation audit — v4.2.0 → v4.3.0

**Applied:** `INV72_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md` (sha256 `6e4df91b…1367`), 91 targets.
**Candidate:** `inv72_accelerated_workload_requirement_v4.2.0_hardened.zip` (sha256 `55c8044a…0247`).
**Date:** 2026-09-23 · **Machine-readable:** `evidence/RTM.json` (per-control status, refs, blockers),
`evidence/RELEASE_EVIDENCE.json` (gate lanes and verdict).

## Four axes, reported separately

| Axis | Result |
|---|---|
| Implementation (RTM, all 100) | **71 present · 22 partial · 6 blocked · 1 N/A-pending · 0 missing** (v4.2.0: 9 · 24 · 0 · 0 · 65 missing · 2 external) |
| Implementation (the 91 checklist targets) | 62 present · 22 partial · 6 blocked · 1 N/A-pending |
| Verification | 163 tests pass under `python` and `python -O`, 0 skips (pk_core now vendored, so the conformance tests run); RTM, deps, manifest lanes PASS |
| pk_core framework gate | GO, 100/100 "satisfied" — **not implementation evidence**: pk_core's default handlers derive findings from contract declarations, several unconditionally; only 5 findings are backed by exercised behaviour (`component.EXERCISED_BANDS`) |
| Production release | **NO_GO** (`tools/release_gate.py`, exit 3) |

"Present" means implemented and verifiable inside this archive. No row has been independently
reviewed, and the checklist's completion rule requires that, so no row is claimed *complete*.

## Release-gate blockers (all need a person or an environment)

1. `ops/OWNERS.json`: every role UNASSIGNED (C009) → governance check fails (12 findings).
2. Seven waivers W-001…W-007 all `pending_approval` → 29 non-present controls are ungoverned.
3. Performance gate FAIL: `pure_match_4096` p99 ≈ 12.9 ms against the contract's 10 ms (thresholds are
   also only PROPOSED, and results come from the cloud build host, not a reference machine).
4. No human release approval.

`tests/test_gates.py::ReleaseGateFalsifierTest` proves the gate is a gate, not a wall: with every input
genuinely supplied it returns GO, and each of 13 single omissions returns NO_GO.

## Blocked / partial / pending, with the reason

| ID | Status | Why |
|---|---|---|
| C009 | blocked | no accountable owner/backup named; tabletop not run |
| C010 | blocked | ADR-0001 PROPOSED; architecture board UNASSIGNED |
| C031 | blocked | passthrough/inference/driver stack is host-owned and unselected (W-003) |
| C047 | blocked | no KMS or encryption available; journal stored in clear (W-004) |
| C098 | blocked | reviews scheduled; none performed; no reviewers |
| C100 | blocked | release gate NO_GO (above) |
| C068 | N/A-pending | INV-72 does no accelerator work; rationale awaits approval; no edge node (W-006) |
| C013 | partial | availability not measurable without a deployment; latency NFR straddles the bound |
| C030, C083 | partial | neighbours absent — contract-level reference adapters only (W-002) |
| C042 | partial | real grants live in the host KeyProvider, never access-reviewed |
| C043, C046 | partial | process sandbox and execution/memory/side-channel isolation are host/GAP-11-owned (W-003) |
| C045 | partial | digest + HMAC only; no asymmetric signature or provenance attestation (W-004) |
| C058 | partial | fencing needs a shared store; no replicated store or leader election here |
| C061–C063, C070, C088 | partial | real measurements, but non-reference host, PROPOSED thresholds, 60 s soak, no fleet scale (W-005) |
| C078 | partial | release lineage attached; no live infrastructure graph exists |
| C080 | partial | alerts and dashboards declared, not deployed |
| C084 | partial | 16-cell CI matrix declared; only CPython 3.11 / Linux x86_64 run |
| C089 | partial | partition/reconnect/stale-leader/restore exercised in-process only |
| C091, C097, C099 | partial | commitments, paging and waiver owners resolve to UNASSIGNED |
| C092, C096 | partial | rollout and runbooks written; never executed or drilled (W-007) |

## Defects found and fixed during this pass

In the v4.2.0 candidate:

1. **Double allocation for the same tenant.** Ownership was tracked per tenant, so a tenant's second
   job was handed the same whole device. The new reservation store occupies a reserved whole device
   for every later request. `match()` keeps the old behaviour for compatibility and is deprecated (D-001).
2. **Evidence bound to the wrong checklist items.** `component.py` attached its matching check to C031
   (pin approved technology) and its isolation check to C041 (threat model). They are now C081 and C046.
3. **No input bounds.** An unbounded inventory iterable was read in full. It is now refused at
   `MAX_INVENTORY + 1`.

In this pass's own code, each caught by its own tests or probes:

4. Journal recovery raised `TypeError`/`KeyError` on structurally valid JSON that was not a record
   (`5`, `[]`, `null`, a dict missing keys). It now refuses with `ACCEL_STATE_CORRUPT`, and the fuzz
   suite carries those shapes.
5. The replay-cache pruning scanned every nonce on every call. The 60 s soak showed p50 growing from
   ~1.0 ms to ~2.7 ms. An expiry heap fixed it: soak p50 ≈ 0.82 ms, flat.
6. The overlay copy re-validated every device, a third time per request. Removing that pass cut the
   governed p50 from ~1.1 ms to ~0.8 ms. The re-validation inside `decide()` stays, for threat T8.
7. Audit export restarted the chain at genesis instead of the exported head, and audit overflow was
   raised after the append. Both fixed and tested.
8. Test design: the capacity test asserted `critical` at 80 % saturation (the threshold is 90 %), and
   the failover test reused nonces across two token minters.

## Measured (cloud build host, CPython 3.11.15, Linux x86_64 — indicative only, not a reference machine)

| Scenario | p50 | p99 | ops/s |
|---|---|---|---|
| pure match, 16 devices | 31 µs | 76 µs | 29.8 k |
| pure match, 256 | 420 µs | 670 µs | 2.3 k |
| pure match, 4096 | 7.1 ms | **12.9 ms** | 135 |
| governed request, 256 devices | 807 µs | 1.50 ms | 1.17 k |
| 50 tenants vs 1 | 818 vs 806 µs | 1.86 vs 1.53 ms | — |
| 60 s soak | 821 µs | 1.68 ms | 1.13 k |

Full data: `evidence/PERF_RESULTS.json`, `evidence/OPTIMIZATION_REPORT.json`.
