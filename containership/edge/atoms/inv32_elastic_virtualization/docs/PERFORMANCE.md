# INV-32 Performance, Capacity and Efficiency (v4.3.0)

Harness: `bench.py` (`run`, `gate`). Evidence: `evidence/bench-results.json` (+ baseline). Controller-owned
latency only; the provider is the deterministic fake. Real-hardware classes, HyperFlux and guest-agent
latency, NUMA/firmware/power-mode capture, thermal throttling and energy/op are **BLOCKED** on real hardware
and the real adapter (the harness records `env` and honours `INV32_HW_CLASS` so the same command produces
comparable results there).

## Measured (CI sandbox, fsync on, 64 guests, 500 iterations, seed 1)
| Operation | p50 | p99 | SLO p99 |
|---|---|---|---|
| decision only (pure policy) | ~0.03 ms | ~0.07 ms | 2 ms |
| memory grow / reclaim (durable e2e) | ~3.4–4.3 ms | ~7 ms | 50 ms |
| vCPU add / remove | ~4.2 ms | ~7–8 ms | 50 ms |
| rollback | ~5 ms | ~8 ms | 60 ms |
| host snapshot | ~0.05 ms | ~0.13 ms | 5 ms |
| audit append (fsync) | ~0.25 ms | ~0.55 ms | 20 ms |
Throughput ≈ 220 durable mutations/s/controller; audit ≈ 0.9 KiB/event; journal ≈ 2.7 KiB/mutation.
Exact numbers: see the JSON (they vary per run and host).

## What "microsecond-scale" means here
Only the decision step is in the tens of microseconds. Durability (≈6 fsyncs per mutation) dominates. A
non-durable fast path is not provided because it would violate REQ-NFR-DUR; ADR-0001 records this.

## Efficiency findings (profiling, cProfile)
1. Full audit-chain verification on every mutation made latency O(n) in history → replaced on the hot path by
   `verify_recent` (64-event window) + full verify at start, in readiness, and every 1024 mutations.
2. `json.dump` streaming to file for `state.json` cost ~50% of CPU → single `json.dumps` + write (≈4× speed-up).
3. `incomplete_ops()` scanned all historical ops → indexed set.
Remaining: 6 journal fsyncs/mutation (could be group-committed — only after measuring on target storage);
`list_guests()` called twice per mutation (redundant query, retained for the post-mutation invariant check).
Batching, zero-copy and kernel-bypass: not applied — no profile shows serialization or copies as dominant,
and batching would weaken per-guest isolation.

## Load scenarios implemented
Steady-state (bench `run`), burst/overload (`test_controller_overload_bounded_no_duplicate_mutations`: 60
concurrent requests, bounded admission), hot-spot guest (`test_at_most_one_writer_per_state_version`), many
tenants (quota property test, 400 randomised ops), recovery after outage (crash injection). Soak ≥ 24 h,
fleet-scale (thousands of guests), audit rotation under load at scale and config reload under traffic at scale
are **BLOCKED** on CI capacity (commands: `bench run --iterations 1000000 --guests 5000`).

## Capacity model
Per controller: mutations/s ≈ 1 / (p50 durable latency) ≈ 200–250; guests/host bounded by provider, not by
INV-32 (state ≈ 150 B/guest in `state.json`); audit growth ≈ 0.9 KiB × mutations → at 50 mut/s ≈ 160 MiB/h
(size `audit_segment_max_events` and export accordingly); state-store IOPS ≈ 7 fsyncs × mutation rate.
Saturation signals: `inv32_inflight_operations / (max_inflight_per_host − safety_reserved_slots)` warn 0.7,
critical 0.9; queue wait p99 > 100 ms; circuit opens. Headroom: `safety_reserved_slots` (default 4) always
free for rollback/quarantine/reconcile. Tenant density: `max_inflight_per_tenant` × tenants ≤ host limit is not
required (admission enforces host bound). Model validation vs load tests at scale: BLOCKED (see above).

## Release gate
`bench gate --baseline evidence/bench-baseline.json --results new.json [--waivers waivers.json]` fails on
p50 > 1.25×, p95 > 1.35×, p99 > 1.5× baseline or any SLO miss, unless an unexpired waiver names
`<op>.<quantile>`. Raw results + env are archived by CI.
