# Performance analysis (M51/M53/M55/M56)

## Copy / serialization / hop analysis (reference path)
| Step | Copies | Serialization | Hops |
|---|---|---|---|
| push | 1 (`bytes(data)` to immutable storage) + 1 hash pass | envelope base64 decode + JSON parse once | 0 |
| start | 1 hash pass over stored bytes (TOCTOU re-check) | none | 0 |
| call | 0 payload copies in-process; provider receives caller objects | token: 1 base64 + JSON parse + 1 Ed25519 verify | 1 (local) — production adds 1 NATS hop per cross-host call |

The dominant per-call cost in the reference control plane is **Ed25519 verification in pure Python** (see `release/BENCHMARK.json`, `auth_verify`). Production must use a constant-time native verifier (`cryptography`/libsodium) or session-level authentication (mTLS) with per-call capability checks only; the benchmark reports both "authenticated call" and "capability-checked call" so the gap is visible.

## Capacity / saturation
`tools/bench.py` sweeps concurrency and records throughput and p99 for the reference control plane; the knee is recorded as `saturation.knee_concurrency`. These numbers are for this container only.

## Edge power / thermal (M55)
**Blocked.** Requires physical edge hardware with power instrumentation. Nothing in this repository measures watts or temperature, and no proxy is substituted (WAIVERS.json W-HW).
