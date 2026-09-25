# INV-61 Performance, Capacity & Power (M28)

Evidence: `evidence/bench_results.json` (produced by `bench/bench.py`), gate: `evidence/perf_gate.json` (`tools/perf_gate.py` against `bench/thresholds.json`). Reference host: 2-vCPU x86-64 Linux container, CPython 3.11.

## Cost anatomy (C065)

| Stage | Share of in-process pipeline | Notes |
|---|---|---|
| Envelope decode + re-encode for MAC input | ~35 % | The MAC is computed over the canonical envelope; decoding then re-encoding is the price of a single canonical form. A future minor may MAC the raw body span instead (needs a frame-layout change). |
| Worker-pool hop (thread handoff) | ~50 % of pooled calls | Removed for `inline=True` exports (direct composition, C066). |
| Metrics / tracing | ~8 % | Label keys cached; spans only when sampled. |
| Response encode | ~7 % | |

Copies: header parse is zero-copy; body is one allocation of exactly the validated length; args bytes are sliced once. No extra network hops: INV-61 adds exactly one TCP round trip per call; multiplexing avoids per-call connection setup.

## Optimisations applied (C066)

Cached record field plans in the codec; `bytes`-based reader with `unpack_from`; inline dispatch option; one connection multiplexing many calls; per-connection write lock instead of per-call sockets. Kernel-bypass and zero-copy I/O are out of scope for a stdlib runtime.

## Capacity model and saturation signals (C069)

`capacity_calls_per_s ≈ workers / mean_callee_s` for pooled exports and ≈ `1 / pipeline_mean_s` per core for inline ones. Saturation signals: `inv61_inflight` approaching `max_inflight`; rising `inv61_requests_total{status="overloaded"|"rate-limited"}`; `inv61_request_seconds` p99 rising while rate is flat; `inv61_connections_rejected_total`. Alert rules: `deploy/alerts.yml`. Scale out when sustained in-flight > 70 % of ceiling for 10 min.

## Bounds (C067)

Frame ≤ `max_frame_bytes`; string ≤ 256 KiB; collections ≤ 65 536; depth ≤ 16; replay cache ≤ 250 000 entries (size it to peak_rate × (window + future skew); when full, calls shed as retryable `overloaded`); idempotency cache ≤ 50 000; tenant table ≤ 10 000; metric series ≤ 1 000 per metric; spans ≤ 10 000; connections ≤ `max_connections`; per-connection mux workers 16; call pool `workers`.

## Power and thermal (C068)

Not measured: no constrained edge hardware was available (W-010). Method for when it is: RAPL / board power meter, idle vs 50 % vs saturation for 10 min each, report J/call and throttling events.
