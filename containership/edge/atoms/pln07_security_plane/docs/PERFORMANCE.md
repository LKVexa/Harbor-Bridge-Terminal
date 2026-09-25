# Performance, capacity and optimisation record (MC-33 .. MC-38)

## Suite
`python -m pln07_security_plane.bench.bench [--quick] --out results.json` — verify latency by depth 0–5, service issue/verify latency, a 1,500-request burst through admission control, and a soak loop that checks p99 drift. Budgets live in `bench/baseline.json`; the gate fails on regression. Reference results from the build host: `bench/results.reference.json`.

## Thresholds (CI ceilings)
| Path | p99 budget |
|---|---|
| `Verifier.verify` depth 0 → 5 | 200 → 750 µs |
| service `verify` (decode + verify + audit) | 3 ms |
| service `issue` (auth + policy + sign + audit) | 5 ms |
| soak drift | last-window p99 ≤ 3 × first-window p99 |

Worst case is bounded structurally: chain ≤ 6 links, scope ≤ 256 items of ≤ 256 chars, request ≤ 64 KiB.

## Optimisation analysis (MC-35)
- **Serialization:** one canonical JSON encode per link for fingerprints; `id` recomputes the legacy digest up the chain. Measured cost is dominated by SHA-256 over small bodies. Caching fingerprints on the frozen dataclass is the next step if depth-5 p99 approaches budget.
- **Copies:** grants are immutable and shared; no deep copies on the verify path.
- **Context switches / network hops:** zero on verify (in-process); revocation lookups are in-memory dict hits after replay.
- **Batching:** revocation writes are fsync'd one by one for durability; batching is deferred until write rate needs it (see capacity).
- **Zero-copy:** not applicable at these payload sizes.

## Resource bounds (MC-36)
Chain depth 5 (policy may lower), scope 256, atom 256 chars, wire chain 6, body 64 KiB, idempotency cache 10k, metrics histogram 10k samples/metric, label values 64/label, span buffer 5k, config history 20.

## Capacity model (MC-38)
Verify is CPU-bound: throughput ≈ cores × 1 / mean service-verify latency (≈ 4–5k ops/s per core on the reference host). Revocation writes are fsync-bound (disk-dependent, typically 1–5k/s on SSD). Saturation signal: `admission.overloaded` rate > 0 or p99 above budget. The bench regression gate guards both.

## Edge power/thermal (MC-37)
Not measured: needs far-edge hardware. External blocker.
