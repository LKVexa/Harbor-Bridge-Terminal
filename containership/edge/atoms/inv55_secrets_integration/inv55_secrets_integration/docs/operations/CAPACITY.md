# Capacity model and saturation signals (checklist #69, DRAFT)

Per instance, in-process reference measurement (`evidence/bench.json`, reference host, not certified): single-thread cached resolve ≈ 0.1 ms, multi-thread throughput recorded under `throughput_rps` (GIL-bound; scale by instances, not threads).
Model: required instances = peak RPS / (0.6 × measured per-instance RPS); provider load = cache-miss RPS = peak RPS × (1 − hit ratio); hit ratio ≈ 1 − 1/(fresh_s × per-secret RPS).
Saturation signals: `inflight/max_inflight` > 0.8, quota denials, lease table > 80 % of cap, breaker state, `telemetry_series_dropped_total` > 0. Fleet-scale numbers are UNMEASURED (W-006).
