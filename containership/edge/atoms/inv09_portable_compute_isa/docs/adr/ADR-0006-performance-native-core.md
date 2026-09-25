# ADR-0006: Native decoder/validator core to meet the latency SLO
Status: proposed. Measured: ~1.7 MiB/s (p99 2.4 s at 4 MiB) vs SLO p99 < 20 ms. Options: (a) Rust
`wasmparser` via a thin FFI with this Python implementation as the differential oracle; (b) narrow the
SLO to ≤ 64 KiB modules; (c) rely on M09 cache hit rate. Recommendation: (a), keep interfaces and tests.
Until decided, the M30 performance gate FAILS and production exit is NO_GO.
