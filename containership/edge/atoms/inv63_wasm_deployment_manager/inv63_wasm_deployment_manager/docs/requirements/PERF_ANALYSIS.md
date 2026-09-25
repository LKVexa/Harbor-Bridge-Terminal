# INV-63 Performance Analysis

| Field | Value |
|---|---|
| Document ID | INV63-REQ-PERF-ANALYSIS |
| INV-63 C-IDs covered | C065, C066 |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Performance reviewer (role), SRE lead (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when `manager.diff`, `store.Journal.append` or `service.op_rollout` change. |

Environment for all numbers: container CI runner, Python 3.11.15, x86_64, 2 CPUs (`perf/results.json`); reference hardware unspecified.

## 1. Applied optimisation (C066)

| Item | Before | After | Evidence |
|---|---|---|---|
| Placement in `manager.Manager.diff` | each new instance selected by `min(hosts, key=(zone_count, host_count, host))` → O(count × hosts) | per-zone min-heaps of `(host_count, host)`; zone chosen by `(zone_count, heap top)`; O(count × zones + count × log hosts) | cold `diff` for 1000 instances on 200 hosts / 10 labels: p50 ~29 ms → ~2.7 ms (recorded 2.71 ms) on the CI container. The ~29 ms baseline is from the pre-4.3.0 run and is not stored in `perf/results.json` |
| Semantic equivalence | — | identical host sequence for spread and pack modes | `tests/test_manager.py::PlacementEquivalenceTest::test_heap_placement_matches_reference` (300 random topologies, 1–11 hosts, 1–4 zones, 0–5 existing, count 0–19, 70% spread) against the reference O(count × hosts) algorithm |

Note: the code comment in `manager.py` names the test as `tests/test_manager.py::test_heap_placement_matches_reference`; its full id is `PlacementEquivalenceTest::test_heap_placement_matches_reference`.

## 2. Identified avoidable costs (C065)

| # | Cost | Where | Estimate | Decision | Why |
|---|---|---|---|---|---|
| P-1 | Runtime state revalidation on every call: `_validate_runtime_state` re-validates and re-tuples all of `actual` | `Manager.diff`, `apply`, `rollout` | O(len(actual)) per call; dominant part of the ~1.95 ms noop diff at 1000 instances | **keep** | Defends against caller mutation of public fields (`test_runtime_state_tampering_is_detected`); well within threshold (p99 3.1 ms vs 10 ms) |
| P-2 | JSON canonicalisation per journal append (`_canon` twice: digest body + line) and SHA-256 | `store.Journal.append` | small vs fsync | **keep** | Required for the tamper-evident chain; cost dwarfed by fsync |
| P-3 | `fsync` per record, and several records per request (e.g. `desired_set` + `lifecycle` ×2 + `idempotency`) | `Journal.append` | dominates request latency on real disks; container result 0.45 ms p50 is likely not representative of edge flash | **defer** (candidate: group commit per request) | RPO 0 depends on it; batching needs a crash-consistency proof and new tests |
| P-4 | `Manager._record` audit event per diff (JSON + SHA-256) kept in an unbounded in-memory `audit_events` list | `Manager.diff` | memory grows with every reconcile, including `tick()` | **fixed** | `reconcile_ns` clears `manager.audit_events` after each diff; the fenced journal is the audit of record |
| P-5 | Full list copies in rollout: `[a for a in manager.actual if ...]` per batch, `_observe()` after each batch, `list(self.running)` in adapter | `service.op_rollout`, `InMemoryLattice.list_instances` | O(batches × actual) | **keep** | Batches are bounded by `count <= 1000`; correctness (fresh observation) outweighs cost |
| P-6 | `Journal.__iter__` copies the whole record list; `op_rollback` scans the full journal | `store.Journal.__iter__`, `service.op_rollback` | O(records) per operator rollback | **keep** | Operator-only, rare |
| P-7 | `_recover` replays the whole journal at startup | `service._recover` | 142 ms / 10k records measured | **mitigated** | `DeploymentService.compact()` reduces replay to one snapshot record (operator-triggered) |
| P-8 | `status()` runs preflight including an fsync probe and `adapter.ping()` twice | `service.status` | one extra lattice round-trip per status | **defer** | Health endpoint frequency not yet defined |
| P-9 | Idempotency record journaled per successful request | `service.handle` | ~1 record/request; the main driver of journal growth | **mitigated** | Needed for exactly-once across restart; `compact()` keeps the last 10k keys |

Rollout starts now go through the circuit breaker (safety, not performance). No other optimisation was applied in 4.3.0.
