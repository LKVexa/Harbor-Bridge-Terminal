# INV-17 Benchmarks

**Controls:** C061-C063 (reproducible harness; C062 percentile/worst-case SLOs), C064 (per-tenant overhead), C065-C066 (copy/serialisation profiling), C070 (regression gate)
**Owner:** UNASSIGNED — owner to fill

No results are recorded in this document. The current results file is
`benchmarks/results/latest.json`; the comparison baseline is `benchmarks/baseline.json`;
targets are in `slo/performance-slo.json` (the contract SLO is "p99 element handoff under 1us
within an instance", `contract::build`). Whether any result meets that target must be read from
the JSON, not from this README.

## Methodology

- Harness: `tools/bench.py` (stdlib, `time.perf_counter_ns`), writes `benchmarks/results/latest.json`.
- Warm-up iterations discarded; multiple repetitions; report p50/p90/p99/p99.9/max and run-to-run variance.
- Record environment in the result: Python version/implementation, OS, CPU model, core count,
  `INV17_SOURCE_REVISION`, config digest (`configuration::digest`).
- Scenarios (intended):
  1. Single-thread handoff: `grant` + `write` + `read` on one `Stream[int]`.
  2. Idempotent write path (`idempotency_key`).
  3. Registry write path (token verify + quotas) vs direct path.
  4. Contended producer/consumer threads with `write_wait`/`read_wait`.
  5. N-stream scaling (registry `buffered_total` cost).
  6. Per-tenant overhead: M tenants × K streams.
  7. `CanonicalCodec` lower/lift and `HttpBody` chunking (copies profiled by `tools/profile_copies.py`).

## Reference profiles

| Profile | Description | Config |
|---|---|---|
| ref-cloud | x86-64 server class, CPython 3.11+ | `config/overlays/cloud.json` |
| ref-far-edge | small ARM/x86 device | `config/overlays/far-edge.json` |
| ref-dev | developer workstation (not for gating) | `config/defaults.json` |

No reference host has been designated; entries are placeholders until an owner assigns hardware.

## Reproduction

```sh
cd inv17_streaming_primitive/..
python -m inv17_streaming_primitive.tools.bench     # or: python inv17_streaming_primitive/tools/bench.py
python inv17_streaming_primitive/tools/perf_gate.py # compares latest.json vs baseline.json; non-zero exit on regression
python inv17_streaming_primitive/tools/profile_copies.py
python inv17_streaming_primitive/tools/capacity.py
```
(Exact invocation depends on the tools' final CLI; see each tool's `--help`.)

## Regression gate

`tools/perf_gate.py` compares `latest.json` against `baseline.json` using thresholds from
`slo/performance-slo.json`. Updating the baseline requires an owner decision (UNASSIGNED).
Soak/burst: `tests/test_soak.py`.

Power/thermal: see `benchmarks/power-thermal.md` (not measured).
