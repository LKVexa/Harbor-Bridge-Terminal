# Service-level objectives (M52/M77)

| SLO | Objective | Measurement (SLI) | Window | Error budget | Alert |
|---|---|---|---|---|---|
| Artifact integrity | 0 components started from mismatched/unsigned bytes | `inv60_operations_total{operation="start",code="OK"}` whose ref lacks a verification record = 0; `DIGEST_MISMATCH`/`SIGNATURE_INVALID` counted as prevented, not as breaches | continuous | none | `Inv60DigestRefusals` (page) |
| Failover | components on a lost host running elsewhere ≤ 10 s after loss is declared | time from `host.lost` ledger record to `component.running` decision record | 28 d | 1 % may exceed | `Inv60FailoverBurst` |
| Routing overhead | control-plane overhead per call: p50 < 0.5 ms, p95 < 1.5 ms, p99 < 3 ms, worst-case < 25 ms | `inv60_call_seconds` minus provider time | 28 d | 1 % may exceed | `Inv60RoutingP99Burn` (14.4× / 1 h fast, 6× / 6 h slow burn) |
| Control-plane availability | 99.9 % of authenticated, authorized mutations return a non-`INTERNAL` result | `inv60_operations_total` | 28 d | 0.1 % | `Inv60OperationLatency` |

Failover timing budget: detector `lost_after_s` (8 s default) + placement + restart must fit in 10 s; the detector default therefore leaves ≤ 2 s for reschedule. Edge overlays raise `lost_after_s` to 30 s and are **excluded** from the 10 s SLO (recorded in WAIVERS.json W-PERF).

The measured baseline for this release is in `release/BENCHMARK.json` (reference control plane, this container — not target hardware).

Support hours, owning team and paging are owner decisions (OWNERSHIP.json) and are not yet filled in.
