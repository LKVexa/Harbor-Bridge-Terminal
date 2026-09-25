# Edge power/thermal benchmark protocol (G13-MC-033 — BLOCKED)

Status: **BLOCKED** — needs far-edge reference hardware and an inline power meter; cannot be measured in the build environment. The protocol is ready:

1. Hardware: target far-edge SKU, fixed governor, ambient 25 °C, inline USB/PoE power meter at ≥10 Hz.
2. Idle baseline 10 min without GAP-13.
3. Workload: `python -m gap13_policy_engine.bench --quick` looped for 30 min at 10 %, 50 % and 100 % of measured single-core throughput.
4. Record: mean/peak W, J per 1 000 evaluations, SoC temperature, throttling events, p99 latency drift.
5. Pass criteria (proposed): ≤ 5 % added mean power at 10 % load; no thermal throttling at 50 %; p99 drift ≤ 20 %.
6. Attach results to the evidence manifest under `edge_power`.
