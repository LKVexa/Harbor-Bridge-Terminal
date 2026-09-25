# Performance (MC-051 .. MC-060)

Harness: `python inv62_edge_topology/tools/bench.py [--quick] --out evidence/bench.json --gate`.
Seeded estates (regions × 20 sites × 50 devices, 5 % GPU devices). Results carry the Python version, machine,
OS and CPU count. Baseline: `perf/baseline.json`; thresholds: `perf/thresholds.json`; gate output:
`perf_gate.json` (status PASS/FAIL, power/thermal always NOT_MEASURED).

## What is measured
engine nearest p50/p95/p99/max at 100 / 1 000 / 10 000 nodes; wire resolve (decode → authn → authz → admission
→ policy → encode) at 1 000 nodes; codec share of wire time; apply throughput; cold start; WAL recovery of
1 000 records; per-tenant heap and latency with 100 tenants; overload at 3× the admitted rate (shed ratio and
served-request p99); peak heap.

## Serialization / hop / copy analysis (MC-055)
* **Serialization:** one JSON decode and one encode per request; measured codec share ≈ 1–15 % of wire time
  depending on graph size. No intermediate re-serialisation (response dict validated in memory).
* **Hops:** zero internal network hops; one transport hop client ↔ instance.
* **Copies:** apply clones the graph once per batch (copy-on-write, O(V+E)) to guarantee atomicity —
  the dominant apply cost; feeds should batch. Reads never copy the graph. Removed in 4.3.0: the 4.2.0 O(E)
  neighbour scan per heap pop (now an adjacency index), full-graph Dijkstra per query (now lazy and
  early-terminating), full partition walk per resolve (now cached per revision).

## Optimisation layer (MC-056)
| Optimisation | Invalidation | Evidence |
|---|---|---|
| adjacency index `Topology._adj` | maintained on every link mutation; property-tested against `links` | `test_random_mutation_sequences_preserve_invariants` |
| lazy early-terminating Dijkstra | none (pure) | fuzz vs Floyd–Warshall reference |
| partitioned-site cache per (revision, cloud) | any mutation bumps revision | election/fault tests |
| batching via atomic apply | n/a | bench apply throughput |

Measured effect (same host): wire resolve at 1 000 nodes p50 9.3 ms → ≈0.8–1.0 ms (see `perf/baseline.json`).

## Power / thermal (MC-058)
Not measurable from this environment (no RAPL/battery/thermal sensors on a known edge device). Status
`open_external`; the gate reports NOT_MEASURED and the exit gate does not count it as passed.
