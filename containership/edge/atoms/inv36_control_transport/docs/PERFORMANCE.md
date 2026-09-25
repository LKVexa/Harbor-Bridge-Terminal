# Performance certification (MC-13)

Harness: `tools/bench.py` (methodology in its docstring). Thresholds: `perf/thresholds.json` (**proposed**, awaiting performance-owner approval). Reference baseline: `perf/baseline-reference.json`.

## Method

- Profiles: `smoke` (PR; 300 crypto iterations per size, 30 handshakes, 200 control ops, 20 sessions) and `full` (release/nightly; 5,000 / 300 / 3,000 / 200).
- Message sizes pinned: 64 B, 1 KiB, 64 KiB; control ops use small bodies; soak uses a mixed 16 B-65,000 B distribution.
- Timing: `perf_counter_ns` (monotonic); 50-iteration warm-up per size; p50/p95/p99/max, mean and standard deviation reported; no outlier removal (tails are the point).
- Every result file carries an environment fingerprint (Python, platform, CPU count, governor, `cryptography` + OpenSSL version).
- Crypto/session processing is measured separately from the full stack; real-vsock end-to-end is **not measured** here (needs a certified VM row).

## Reference results (authoring sandbox: Linux-6.18.44-fc-v37-x86_64-with-glibc2.39, 2 vCPU Xeon 2.1 GHz, Python 3.11.15, cryptography 46.0.7, OpenSSL 3.5.6 7 Apr 2026; `full` profile)

| Measurement | p50 | p95 | p99 | max | rate |
|---|---:|---:|---:|---:|---:|
| seal+open 64 B | 5.09 us | 6.8 us | 12.58 us | 39.39 us | 183,406 msg/s |
| seal+open 1 KiB | 9.11 us | 19.68 us | 36.87 us | 97.12 us | 97 MB/s |
| seal+open 64 KiB | 275.69 us | 328.91 us | 389.87 us | 3387.46 us | 233 MB/s |
| PK_CTRL_HS/1 handshake (full stack, in-memory stream) | 2.19 ms | 2.84 ms | 4.28 ms | 5.93 ms | 427.6 sessions/s |
| control-op round trip (send -> authorize -> dispatch -> reply) | 310.02 us | 514.53 us | 911.81 us | 7160.01 us | 2875.2 ops/s |

Other: import/startup 31 ms; memory per established session pair (both ends) 22,791 B at 200 sessions; process RSS 43 MB; overload run (1,000 offers, HWM 64): depth bounded at 80, CRITICAL admitted preferentially. The contract SLO (64 B seal+open p99 <= 50 us on a certified target) holds in this environment; this is **not** a certified profile.

## Profiling findings (cProfile, 1,500 control ops)

- ~70 % of round-trip time is thread hand-off inside the in-memory test stream (lock waits), i.e. harness cost, not transport cost; AES-GCM-SIV encrypt+decrypt is ~2 %.
- Metric label normalisation was ~9 % - memoised in 5.1.0 (bounded memo), full suite re-run afterwards (MC-13.020).
- Copies: `Session.seal/open` copy caller buffers once (`bytes(...)`) to freeze input; `Connection` copies once from the receive buffer. `memoryview` reuse was evaluated and not adopted: the copy protects against caller mutation during AEAD processing and costs < 1 us for control-sized frames.
- Batching: not adopted - it would couple independent authoritative messages and add latency; ordering is per session anyway.
- Zero-copy / kernel-bypass: not applicable to vsock at control-message sizes; no such optimisation is used (no security/compatibility trade-off introduced).
- Socket buffer sizing: default 256 KiB (`vsock.DEFAULT_BUFFER`); empirical tuning requires real vsock rows (open).

## Capacity model

Per session the work is O(message): crypto CPU ~5-10 us per small frame, so a single core sustains ~100k small frames/s of crypto; in practice the agent's Python dispatch (~340 us CPU per round trip in the reference harness) dominates, giving ~2,900 control ops/s per process-core. Handshakes cost ~2.3 ms CPU each (~430/s per core), so reconnect storms, not steady traffic, set the headroom requirement.

Saturation signals: `inv36_saturation_ratio` (queue depth / HWM) > 0.7 sustained; handshake p99 > 20 ms; control-op p99 growth > 2x baseline; `OVERLOADED` rate > 0; CPU > 70 % of allotted cores; active sessions > 80 % of `max_sessions`.

Safe operating envelope (reference env only, per agent process): <= 1,500 control ops/s sustained, <= 200 handshakes/s bursts, <= 256 sessions, 64 per tenant. Headroom target: 50 % below the measured saturation point. Overload threshold: HWM (256 queued) - optional traffic shed first.

Quotas and fairness: per-tenant session limit (64) and admission quota (64 in-flight) - fleet simulation with 8 tenants gives equal sessions per tenant (+/-1).

Validation against independent load runs: pending (needs certified rows).

## Regression gate

`bench.py --compare` applies absolute limits (smoke-profile safety net) and relative limits (35 % tolerance, 5 us noise floor) against the baseline; CI fails on regression; accepted regressions need a waiver with owner and expiry (`perf/thresholds.json` `waivers`, `governance/waivers.json`). Baseline and candidate results are archived as CI artifacts. Power/thermal: not measured (waiver W-003 proposed).

## Soak finding (60 s, 112,937 frames, 1,132 sessions, 350 key rotations)

FD and thread counts stayed flat and p99 was stable (1.20-1.27 ms per window). RSS rose ~14 MB over the run. Tracing showed the growth is the op_id dedup window (`recovery.DedupWindow`, TTL 600 s, cap 65,536 entries) filling toward its cap; with the cap reduced to 1,000 the Python heap stayed flat (1.6-1.7 MB). The window is bounded by design (worst case ~10 MB per endpoint). The 6-hour certification soak must confirm the plateau.
