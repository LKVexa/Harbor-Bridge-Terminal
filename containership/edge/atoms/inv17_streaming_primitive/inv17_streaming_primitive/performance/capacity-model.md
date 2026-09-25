# INV-17 Capacity / Saturation Model

**Controls:** C069
**Owner:** UNASSIGNED — owner to fill
**Measured values:** none in this document. Inputs come from `benchmarks/results/latest.json` (written by `tools/bench.py`); the model is evaluated by `tools/capacity.py`. SLO targets: `slo/performance-slo.json`.

## Hard limits enforced by code (element counts)

| Limit | Default | Enforced by |
|---|---|---|
| Outstanding credit per stream | `StreamConfig.max_credit` = 1024 | `stream::Stream.grant` |
| Buffered elements per stream | `StreamConfig.max_buffer` = 1024 | `stream::Stream.write` |
| Idempotency keys remembered per stream | `StreamConfig.idempotency_window` = 1024 | `stream::Stream._remember` |
| Streams per tenant | `TenantQuota.max_streams` = 64 | `control::StreamRegistry.open` |
| Buffered elements per tenant | `TenantQuota.max_buffered` = 65 536 | `control::StreamRegistry.write` |
| Buffered elements per instance | `global_buffer_budget` = 1 048 576 | `control::StreamRegistry.write` |
| Replay-cache nonces (live single-use only; full → fail closed) | 65 536 | `security::CapabilityAuthority` |
| Decision log | 256 entries | `control::StreamRegistry._decide` |
| Audit ledger | **unbounded** (grows per event) | `security::AuditLedger.events` |
| Revocation set | **unbounded** | `security::CapabilityAuthority._revoked` |

## Memory model

```
M_instance ≈ Σ_streams [ S_stream + buffered_i * (S_ref + S_elem_i) + keys_i * S_key ]
           + nonces * S_nonce + audit_events * S_event + M_baseline
```
with `buffered_i <= min(max_buffer, credit granted)` and `Σ buffered <= global_buffer_budget`
(only when writes go through the registry). `S_elem` is application-defined and not bounded by INV-17.
Per-object sizes (`S_*`) are to be measured by `tools/capacity.py` / `tools/profile_copies.py`.

## Throughput / saturation model

- Each `Stream` operation takes one per-stream `RLock`; under CPython's GIL, aggregate
  throughput across streams is bounded by single-core interpreter speed.
- Registry `write` adds token verification (HMAC-SHA256 + JSON decode) and an O(N_streams)
  `buffered_total` scan under the registry lock, so registry write cost grows with open-stream count.
- `read_wait`/`write_wait` poll in 50 ms slices (`stream::Stream._wait`), bounding cancellation latency.

Saturation indicators: `inv17_elements_buffered` approaching `global_buffer_budget`,
rising `inv17_load_shed_total`, `inv17_breaker_open = 1`, health `degraded` with buffer-fill reasons.

## Headroom procedure

1. Run `python tools/bench.py` (writes `benchmarks/results/latest.json`).
2. Run `python tools/capacity.py` to derive per-stream/per-instance cost and the stream count at which the configured budget or CPU saturates.
3. Keep production config at or below a proposed 70% of the derived knee (PROPOSED policy, not approved).
