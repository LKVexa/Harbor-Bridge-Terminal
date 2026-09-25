# Benchmarks, capacity and copies (C061-C070, X014)

**What is measured:** INV-26's own restore/capture path end-to-end through `SnapshotService.handle`
(authn, authz, grant verify + durable CAS, admission, metadata, blob read, AES-256-GCM per chunk, DEK
unwrap, framing, VMM load/resume, entropy injection) with the **reference VMM**. The real VMM's restore
time is **not** included, so these numbers are INV-26 *overhead*, not the contract SLO. Every run records
`certifiable: false`; the gate refuses to treat them as SLO evidence. Raw samples → nearest-rank
percentiles; environment fingerprint in each file.

Reproduce: `python -m inv26_microvm_snapshotting.tools.bench --profile quick|full --out BENCH.json`.

## Restore path (ms) — build host (container, x86_64, Python 3.11, cryptography 46.0.7, no KVM)
| Image | Before PERF-1 p50 / p99 | After PERF-1 p50 / p99 | Evidence |
|---|---|---|---|
| 1 MiB | 5.81 / 14.19 | 2.70 / 4.63 | `evidence/BENCH_PRE_OPT.json`, `evidence/BENCH.json` |
| 16 MiB | 76.01 / 91.71 | 31.92 / 40.99 | same |

**PERF-1 (C066):** the whole-blob SHA-256 was on the restore hot path although the per-chunk GCM tags already
authenticate every byte (with index/total/final and the security context in the AAD). Moving it to capture
read-back and the scrub removed ~49 ms of ~78 ms decrypt time at 16 MiB (hashlib ran at ~320 MB/s on this
host). Decryption now uses `memoryview` slices and a single join. Security unchanged: all tamper tests still
reject (now as `SNAP_CIPHERTEXT_INVALID`), and `verify_digest=True` still distinguishes storage corruption.

## Copies and allocation (C065)
Per restore of an N-byte image: 1× ciphertext read, 1× plaintext chunk list + 1× join, 1× unframe slice,
1× tmpfs memory file for the VMM ⇒ peak Python allocation ≈ 3× image (measured `peak_alloc_over_image`
in `evidence/BENCH.json`). Remaining candidates (DEBT-1): verify all tags first, then stream-decrypt straight
into the tmpfs memory file; Firecracker UFFD backend for lazy paging.

## Load (reference VMM) — see `evidence/BENCH.json` `load`
Steady (4 workers) and burst/overload (16 workers against `max_inflight=16`, `per_tenant=8`) record
throughput, latency and admission rejections separately from unexpected errors (which must be zero).

## Capacity model (C069)
Per node: restores/s ≈ min(admission `max_inflight` / p50 restore time, CPU cores × (1000 / cpu_ms per
restore)); the AES-GCM + copy cost scales linearly with image size (~2 ms/MiB on this host after PERF-1).
Saturation signals: `inv26_inflight` near `max_inflight`, `inv26_admission_rejected_total{reason="queue full"}`
rising, restore p99 rising while CPU is pegged. **Consequence for the SLO:** with whole-image decryption,
a 10 ms p99 is only reachable for images of a few MiB on this class of CPU (ADR-0001 consequence, SLO.md). Measured load on this 2-core host: ~165-180 restores/s of 1 MiB images, CPU-bound.

## Regression gate (C070)
`bench/baseline.json` + `tools/bench.py --compare` fail CI when restore-path p99 exceeds 1.5× baseline + 2 ms
at any measured size, or when load scenarios produce unexpected errors. `evidence/PERF_GATE.json`.

## Not measured (BLOCKED_EXTERNAL)
Real VMM restore, cold-boot comparison, power/thermal on edge hardware (C068), fleet-scale soak (C088), network/KMS
latency injection on real services.
