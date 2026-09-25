# Performance and capacity (INV30-GAP-040..047, GAP-059 · INV-30-C061–C070, C088)

* **Harness (C061):** `bench.py` — seeded, records host fingerprint, Python version, enforcement backend.
* **Thresholds (C062):** `config/perf_thresholds.json` (p50/p95/p99/max per op + recovery).
* **Workloads (C063, C088):** steady, burst/overload (admission forced to 0 → 100 % shed), scale (8 tenants),
  recovery (emergency disable → re-bootstrap). Soak: `INV30_SOAK_ITER=1000000 python -m …bench` (long run, CI nightly).
* **Per-tenant overhead (C064):** `per_tenant_p50_us` + `service_overhead_vs_model_p50_x` (≈65×: the service cost is
  HMAC + JSON canonicalisation + schema validation, not the capability check).
* **Optimisation analysis (C065, C066):** dominant costs are (1) canonical-JSON + HMAC per request, (2) schema walk,
  (3) audit/decision records. Safe optimisations: batch API (`max_batch` 128) amortising auth; precompiled schema
  validators. Unsafe (rejected): caching authorization across requests, skipping grant verification. Zero-copy /
  kernel bypass not applicable to the model; relevant only to the native helper IPC (use a persistent helper with
  shared-memory ring — future work).
* **Saturation model (C067, C069):** saturation = inflight / max_inflight; alert ≥ 0.8; memory ≈ 1 KiB per handle
  → 1 048 576 handles ≈ 1 GiB ceiling; queue bounded by admission.
* **Power/thermal (C068):** **not measured** — requires edge hardware with RAPL/INA sensors. Blocked.
* **Regression gate (C070):** `bench.regression` → release gate blocker.
* **Fleet-scale (C088):** single-node harness only; fleet-scale requires the estate test cluster. Blocked.
