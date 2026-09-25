# Performance, capacity, optimization (MC-034..MC-039)

## Targets (ms) — `perf/bench.py::TARGETS_MS`
| Operation | p50 | p95 | p99 | Evidence |
|---|---|---|---|---|
| create/validate | 0.05 | 0.2 | 0.5 | `evidence/benchmarks.json` (this host) |
| Firecracker plan build | 0.1 | 0.5 | 1.0 | same |
| admission decision | 1 | 5 | 10 | same |
| token verify | 0.1 | 0.5 | 1.0 | same |
| cold boot (real) | 60 | 100 | 125 | NOT_TESTED (KVM host) |
| stop + cleanup (real) | 10 | 30 | 50 | NOT_TESTED |

Regression gate: p95 > 1.5 × baseline (`benchmarks/baseline.json`) FAILS (MC-039).

## Fan-out limits (MC-037)
Per instance: 1–32 vCPU, 32–131072 MiB, ≤4 drives, ≤4 NICs, 1 vsock. Per node: `max_instances`,
`max_instances_per_tenant`, vCPU/memory headroom (`Capacity`), admission queue + per-tenant queue,
1000 metric series/metric, 10 000 spans, 1 M journal entries, 64 KiB API responses, 64 KiB VMM output.
Density model: `max_instances ≤ floor((host_mem − reserve) / (guest_mem + 64 MiB VMM overhead))`.

## Optimization analysis (MC-036, P2)
Control path is allocation-light and syscall-free except journal fsync (one per admission state) — the
dominant cost; batching fsyncs is the next optimization if admission p95 misses. Data path (copies,
context switches, zero-copy) is owned by INV-35 and is `NOT_APPLICABLE` while `datapath_policy=disabled`.

## Power/thermal (MC-038, P2)
Disposition: **NOT_APPLICABLE for cloud/datacenter profiles**; far-edge profile requires measurement
before certification (tracked debt `DEBT-038` in `release/WAIVERS.json`).
