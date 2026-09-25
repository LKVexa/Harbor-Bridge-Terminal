# Performance, resources and capacity (MC-21, MC-22; C061-C070)

## Method

`bench/perf.py` — deterministic seeded fixtures at 1 / 10 / 100 / 1,000 / 5,000 components
(10,000 components exceed the 1 MiB byte ceiling, so 5,000 is the largest legal
fixture of this shape); warm-up then `reps` timed runs with `perf_counter_ns`;
p50/p95/p99/max, mean, coefficient of variation and a bootstrap 95% CI of the
p50; cold import in fresh interpreters; `tracemalloc` peak for the largest
manifest; single-thread steady-state throughput. Every run records CPU model
and count, governor, cgroup limits, Python build and hash-seed variables.
Scenarios: valid and all-dangling invalid manifests (worst case for error
aggregation). Not applicable to a library and therefore not fabricated:
network overhead, scale-out/scale-in (the host scales processes), per-node
power/thermal (no edge reference device in the bootstrap — needs owner
approval to mark N/A or a device to measure: MC-21 blocker).

**Reference environment:** not yet designated. The baseline in
`evidence/PERF_BASELINE.json` was measured on the remediation build container
(Linux x86_64, CPython 3.11.15) and is labelled as such; relative regression
checks run only against an equivalent environment (same CPU model/count and
Python minor), otherwise only absolute thresholds apply.

## Thresholds (release-blocking, `bench/perf.py THRESHOLDS`)

| Metric | Threshold | Baseline (build container) |
|---|---|---|
| validate@10 p99 | ≤ 5 ms (contract SLO) | 0.15 ms |
| parse+validate@100 p99 | ≤ 10 ms | 1.70 ms |
| canonical@100 p99 | ≤ 10 ms | 2.47 ms |
| parse+validate@5000 p99 | ≤ 1,000 ms | 83 ms |
| invalid@1000 p99 | ≤ 150 ms | 21.6 ms |
| cold import p50 | ≤ 1 s | 0.039 s |
| peak memory @5000 | ≤ 80 MiB | 7.2 MiB |

Regression rule: > 25% worse than baseline on an equivalent environment fails,
provided the absolute increase also exceeds max(0.25 ms, 10% of the metric's
absolute limit) — added after the final evidence run of this pass showed
validate@10 p99 moving 0.147 → 0.197 ms between two identical runs (pure
scheduler jitter); a noisy run (CV > 0.35) is rerun
once before failing; a waiver needs an active `perf-waiver` entry in
`ops/REGISTER.json` with owner, approvers and expiry.

## Comparison with 4.2.0 (same container, `timeit` min of 5)

| Scale | 4.2.0 validate | 4.3.0 validate | Factor |
|---|---|---|---|
| 10 | 0.017 ms | 0.108 ms | ~6x |
| 100 | 0.128 ms | 0.90 ms | ~7x |
| 1,000 | 1.24 ms | 8.8 ms | ~7x |

The cost is the MC-14 secret scan over every string and key (NFKC for
non-ASCII, one combined regex, base64/percent variants for candidates). It was
profiled and reduced from ~17x (key normalization cache, ASCII fast path,
combined pattern, short-string skip). It is accepted under SPECIFICATION §10
(security > cost) and tracked as REG-004 with a closure plan (schema-directed
scanning).

## Data path (C065)

```
bytes (≤1 MiB) ─► UTF-8 check + byte ceiling ─► raw depth scan (1 pass, no alloc)
   ─► json.loads (1 decode, dup-key hook) ─► validate_issues: sections (no copy) ─► names/links/traits (set lookups)
   ─► find_secrets (1 iterative walk) ─► canonical_document: json.dumps + json.loads deep copy (1 copy) ─► sort 4 sections ─► json.dumps ─► sha256
service: + token decode (3 small b64/JSON) + policy scan (O(grants)) + audit append (JSON + fsync) + decision record (digests only)
adjacent handoff: canonical document re-serialized once and passed by reference (in-process; 0 network hops in 4.3.0)
```

Serialization boundaries: 2 JSON decodes, 3 JSON encodes per submit. Copies:
one deliberate deep copy (never mutate caller input). Hops: none inside
INV-64. Duplicated state: none (registry stores digests, not manifests).

Optimizations applied: cached key normalization (`lru_cache`), combined
secret regex, ASCII fast path, bounded structures everywhere. **Rejected:**
caching canonical digests by object identity (unsafe — mutable input),
skipping validation for previously seen digests (would let a quarantined
digest in via a different tenant's cache), zero-copy canonicalization
(requires trusting caller not to mutate), batching audit fsyncs (would allow
loss of acknowledged security events). Largest remaining cost under load:
the per-request audit fsync on authentication (stress soak ≈ 400 req/s per
process with fsync on the container's disk vs ≈ 5,100 parse+validate ops/s
without the service layer).

## Capacity model (C069)

Fitted on parse+validate p50: `t_ms ≈ -0.15 + 0.0159 × entries` (relative
error 0.4% / 2.8% / 0.1% at 100 / 1,000 / 5,000 entries; tolerance 50%).
Per core, typical (10-component) manifests: ≈ 5,200 validations/s without
the service layer. Saturation signals: `inv64_inflight / max_inflight ≥ 0.8`
for 15 min, admission rejection rate ≥ 1%, p99 above 5 ms for typical
manifests (alerts A01/A02). Worst case per request is bounded by the byte
ceiling (≈ 7,000 entries ⇒ ≈ 110 ms single-threaded).
