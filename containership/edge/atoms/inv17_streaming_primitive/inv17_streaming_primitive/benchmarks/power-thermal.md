# INV-17 Power / Thermal Measurement

**Controls:** C068
**Status:** **not measured; waiver pending.** No hardware access with power instrumentation was available. No waiver has been approved.
**Owner / waiver approver:** UNASSIGNED — owner to fill

## Why it matters

The far-edge profile (`config/overlays/far-edge.json`) targets constrained devices where
thermal throttling can reduce throughput and lengthen credit stalls, pushing health to
`degraded`/`unhealthy` (`control::StreamRegistry.health`).

## Methodology (to be executed when hardware is available)

1. Reference devices: one per tier (cloud, far-edge minimum). Record SoC, governor, ambient temperature, cooling.
2. Instrumentation: external power meter (preferred) or RAPL / on-board sensors; sample >= 10 Hz; SoC temperature from `/sys/class/thermal`.
3. Workloads: the `tools/bench.py` scenarios at 25/50/75/100% of the saturation knee from `tools/capacity.py`, each for >= 30 min steady state, plus an idle baseline.
4. Metrics: energy per million elements (J), average/peak W, time-to-throttle, throughput under throttle, p99 latency under throttle.
5. Overload check: under throttle, confirm `LoadShed`/`CreditExhausted` bound memory (no growth beyond `global_buffer_budget`) and health signals change.
6. Output: append to an evidence entry referenced by `tools/evidence_bundle.py`; never inline numbers here.

## Waiver request (draft)

- Scope: all tiers, v4.3.0.
- Rationale: no instrumented hardware; INV-17 is CPU-bound in-process code with memory bounded by configuration, so the primary thermal risk is throughput reduction, which is covered by existing overload controls.
- Compensating controls: `global_buffer_budget`, circuit breaker, health stall thresholds.
- Expiry: to be set by approver. Approver: UNASSIGNED — owner to fill.
