# PLN-05 efficiency and resource-bounds analysis

Measured on the 4.2.0 reference run (CPython 3.11.15, Linux x86_64 container; `benchmarks/baseline.json`, cProfile of 5 000 decisions). Numbers are from this environment only.

## Decision data path (per sample)

reporter → (adapter, 1 network hop, TLS) → `wire.parse_bytes` (1 decode) → `wire.validate` → `iam.authenticate` (1 base64 + 1 JSON decode + 1 HMAC) → `authorize` → scope lookup (dict) → `controller.observe` (O(1)) → build target → `wire.validate` (outbound) → `StateStore.save` (1 JSON encode + 1 HMAC + write/fsync/rename, only when `state_dir` set) → `sink.apply` (in-process call; 1 hop in a real adapter) → explain record (1 dict) → metrics/log/trace.

| Quantity per decision | Count |
|---|---|
| JSON decodes | 2 (payload, token body) |
| JSON encodes | 1 with persistence (state), 0 without; +1 per log record if a stream is attached |
| HMAC computations | 1 (token) + 1 (state, if persisted) |
| schema validations | 2 (inbound demand, outbound target) |
| process/thread boundaries | 0 inside the library (single lock hold) |
| network hops | 2 in a deployment (in, out) + lease renew every `lease.duration_s − renew_before_s` (10 s), not per decision |
| duplicated state | explain record duplicates ~1 KB of decision context (bounded by `explain.retention`); persisted state ≈ 1–3 KB/scope |

## Profile (5 000 decisions, 1.89 s under cProfile)

schema validation 38 % (`wire.validate` 0.72 s cumulative, two per decision); token authentication 11 %; depth pre-scan 4 %; redaction 6 %; explain 5 %; controller < 1 %. Payload in: 215 bytes typical.

## Hard bounds

| Resource | Bound | Source |
|---|---|---|
| inbound queue | `queue_capacity` (1 024), control reserve 32 | reliability.AdmissionController |
| retries | `retry.max_attempts` 4 × budget 20 % × deadline 10 s | reliability.RetryPolicy |
| concurrent decisions | 1 per plane (serialised lock) | plane |
| fan-out | 1 sink + 1 coordination + 1 audit per decision; no broadcast | plane |
| replay cache | 10 000 nonces × ~100 B | iam |
| seen ids | 256 per scope | plane |
| explain | `explain.retention` (10 000) × ~1 KB | plane |
| audit | window 4 096 + pending 256 | audit |
| logs / spans | 2 048 / 2 048 | telemetry |
| metric series | `telemetry.max_series` (10 000) | telemetry |
| sink history (reference consumer) | 10 000 | state.FencedSink |

**Bound product:** worst-case resident memory ≈ explain 10 MB + nonces 1 MB + logs/spans 2 MB + audit 4 MB + sink 10 MB + per-scope state (S × ~2 KB) ⇒ ≈ 27 MB + 2 KB·S; measured peak 34 MB for 10 000 decisions (includes interpreter overhead), and the 60 000-decision soak shows < 5 % growth after the bounded stores fill. CPU is bounded by throughput: ~130 µs CPU/decision ⇒ one core sustains ~7 000 decisions/s.

## Optimisation decision records

- **ODR-01 keep outbound validation.** Validating every emitted target costs ~19 % of decision time; kept because it is the last guard for NFR-BOUNDS (no out-of-contract target can leave). Rejected alternative: validate only in tests.
- **ODR-02 no zero-copy / kernel bypass.** The library has no network path; decode+HMAC dominate and are already C-implemented in CPython. Waiver W-002 records this.
- **ODR-03 batching.** `enqueue_demand` + `process(n)` batches under one lock hold; reaction SLO is per sample, so coalescing samples of one scope is *not* done (it would hide a threshold breach).
- **ODR-04 caching.** Compiled regex cache for schema patterns (`wire._PATTERNS`); config snapshot is immutable so reads need no copy. Stale-cache risk: none (snapshots swap by reference).
- **ODR-05 observability cost.** Trace-all vs trace-none differs by ≈ 0.01 ms p95 (baseline `observability_p95_ms`); sampling default 10 % retained.
- **ODR-06 crypto cost.** Token verification ≈ 10 µs (`auth_verify_us`); persistence adds ≈ 1 ms p95 (fsync) — the dominant cost when durable state is on, accepted for NFR-RPO = 0.

Edge power/thermal: **not measured** (no sensors in the reference environment) — waiver W-001; GAP-10's `ceiling.lower` is the compensating control. Optimisations above preserve determinism: none changes decision logic.
