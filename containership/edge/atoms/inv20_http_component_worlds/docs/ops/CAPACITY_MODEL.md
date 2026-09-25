# Capacity model (component 14)

Enforced limits (config `limits.*`, all bounded by schema): global concurrency 64, per-tenant 16,
per-workload 16, queue 128, 8 chunks in flight per stream, 1 MiB body, 8-way fan-out, 32 outbound
connections, 8 per destination, header 100 fields / 16 KiB, trailers 16 fields / 4 KiB.

Model: `max_rps ≈ min(concurrency / (dispatch + user + upstream latency), cpu_cores / cpu_per_req)`;
memory ≈ `concurrency × (stream_chunks_in_flight × chunk_size × 2 + header_bytes)` + base.
With defaults and 64 KiB chunks: 64 × (8 × 64 KiB × 2 + 16 KiB) ≈ 65 MiB worst case per instance.
Saturation indicators: `saturation{resource}` ≥ 0.9, `E_OVERLOADED` rate, queue_wait p99.
Scale-out trigger: queue_wait p99 > 50 ms for 5 min or saturation ≥ 0.8; scale-in below 0.3 for 30 min.
Headroom: 30 %.
Validation against controlled-hardware load tests: **pending** (bench/ baseline was a shared sandbox).
