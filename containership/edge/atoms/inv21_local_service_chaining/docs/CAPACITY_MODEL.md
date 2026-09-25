# INV-21 Capacity Model and Saturation Signals

Per host, with measured single-thread cost `s_local` (p50 of `prod_local_cached`) and `s_remote` (p50 of remote hop, excluding peer handler):

* CPU seconds per second consumed by chaining = `λ_local·s_local + λ_remote·s_remote_client` (+ handler cost, owned by callee).
* In-flight required ≈ `λ·(W_handler + s)` (Little's law). Set `max_in_flight` ≥ 1.5× the p99 of this estimate; per-tenant cap = `max_in_flight / expected_active_tenants × fairness_factor (2)`.
* Fan-out: each root call may create at most `max_depth` nested hops on the call stack; admission charges only the root, so nested work is bounded by depth × fan-out of the handlers (handler responsibility, visible via `inv21_hops_local_total` per callee).
* Memory: decision ring `max_telemetry_events × ~400 B`; audit ring `memory_max × ~500 B`; residency `≤ 10 000 × ~300 B`; breaker ≤ 4096 keys; metrics ≤ 2048 series. All bounded by construction.

Measured (authoring container, CPython 3.11, x86_64 — `evidence/bench.json`, every decision audited): `prod_local_cached` p50 ≈ 49 µs / p99 ≈ 124 µs; uncached (thread-pool policy guard) p50 ≈ 139 µs; 4.x compat path p50 ≈ 22 µs / p99 ≈ 58 µs; remote loopback p50 ≈ 390 µs; HTTP loopback p50 ≈ 1.3 ms; 200 tenants add no measurable p99 overhead. Profiling shows the per-decision audit record (canonical JSON + HMAC + SHA-256) is the largest single cost on the local path; before grants were audited (first pass) the cached path measured p50 ≈ 18 µs.

**Saturation signals**: `inv21_saturation_ratio` (in_flight / max) — warn ≥ 0.7, page ≥ 0.9; `inv21_admission_shed`; `inv21_refused_total{reason="provider_unavailable"}`; `inv21_residency_stale_hits`. Scale out (more hosts) when saturation ≥ 0.7 for 15 min; raise `max_in_flight` only if CPU headroom ≥ 30%.

**Contract SLO status**: p99 < 20 µs local dispatch is **NOT MET** in CPython on the authoring machine (p99 ≈ 124 µs production cached path with full auditing; ≈ 58 µs on the unauthenticated 4.x path). Options recorded for the owner in `governance/waivers.json` (WAIVER-003): revise the SLO, move audit signing to an asynchronous batched writer (keeps fail-closed semantics only if the call waits for the batch), or a native fast path.
