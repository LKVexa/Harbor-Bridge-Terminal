# INV-63 Capacity Model

| Field | Value |
|---|---|
| Document ID | INV63-REQ-CAPACITY |
| INV-63 C-IDs covered | C069 |
| Status | DRAFT — pending approval |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Service owner (role), Performance reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when `perf/results.json` is re-baselined. |

All inputs are from `perf/results.json` (container CI, 2 CPUs, fake lattice, reference hardware unspecified). Real Wadm/NATS latency and real-disk fsync are not included; treat every figure as an upper bound until re-measured.

## 1. Inputs

| Symbol | Value | Source |
|---|---|---|
| R_max | 2008 req/s (noop reconcile, single process) | `throughput_noop_reconcile_rps` |
| t_req | 0.446 ms p50 / 1.003 ms p99 | `handle_reconcile_noop_ms` |
| t_diff(1000) | 2.71 ms cold p50 | `diff_1000_cold_ms` |
| B_desired | 2670 bytes of journal per `set_desired` (all records it causes) | `per_tenant_overhead.journal_bytes_per_desired` |
| t_replay | 142 ms per 10k records → ~14.2 µs/record | `replay_10k_records_ms` |
| J_max | 256 MiB | `store.Journal.max_bytes` |
| M_10k | 18.6 MB peak traced allocation over 10k requests | `tracemalloc_peak_10k_requests_mb` (old key `rss_growth_10k_requests_mb` in current results.json) |

## 2. Model
- **CPU / request rate:** sustainable rate ≈ min(`max_inflight` limits, R_max × cores_effective). Service is effectively single-threaded per process (GIL); plan at 50% of R_max ⇒ ~1000 req/s per instance on CI-class CPU. With a real lattice, each non-noop reconcile adds `(starts + stops) × lattice RTT` (not measured).
- **Tick cost:** one `tick()` = Σ over desired namespaces of `reconcile_ns` ≈ N_ns × (t_diff(count) + lattice `list_instances`). With `reconcile_interval_s=30` and noop reconciles, N_ns up to ~10^4 fits in < 10% of an interval by CPU; lattice `list_instances` is called per namespace (not cached) and will dominate — measure with live Wadm.
- **Journal growth:** bytes/day ≈ 2670 × desired changes/day + ~idempotency record size × API requests/day (every non-`explain` request, including noop `reconcile`, appends one `idempotency` record). Time to J_max = 256 MiB ÷ growth rate. Example: 1 API req/s sustained with ~300-byte idempotency records ⇒ ~26 MB/day ⇒ limit in ~10 days. At J_max all writes fail `INV63-E-QUOTA` until an operator runs `DeploymentService.compact()` (after a backup), which shrinks the journal to one snapshot record (desired state + ≤ 10k idempotency keys).
- **Restart time:** t_restart ≈ records × 14.2 µs; at J_max (~10^6 records of ~250 B) ≈ 14 s + preflight.
- **Memory:** bounded buffers — `Logger` 50k records, `Tracer` 10k spans, `DecisionLog` 100k decisions, idempotency LRU 10k, token nonce cache 100k, metric label sets 2000 per store (counters, gauges, histograms — shared across all metric names; excess dropped and counted in `Metrics.dropped_series`), histogram samples 10k per series (decimated). `Manager.audit_events` is cleared after every service diff (PERF_ANALYSIS P-4).
- **Far-edge:** `edge-site-a` caps `max_inflight=8`, `queue_depth=64`; within the offline window each reconcile of a namespace appends one `offline_intent` record — over 86400 s with `reconcile_interval_s=120` that is 720 records per namespace per day.

## 3. Saturation signals → metrics → alerts (`observability/alerts.json`)

| Resource | Signal | Metric (Prometheus, `inv63_` prefix) | Alert / class / severity |
|---|---|---|---|
| Request capacity | rate approaching capacity | `inv63_requests_total` | `INV63HighRequestRate` — ordinary_load — info, no page (`capacity_rps` must be set to the approved per-instance rate; proposed 1000) |
| Admission | shedding | `inv63_errors_total{code="INV63-E-OVERLOADED"}` | `INV63Degraded` — degradation — SEV3, no page |
| Tenant fairness | rate/quota rejections | `inv63_errors_total{code="INV63-E-QUOTA"}` → `alerts{cls="ordinary_load"}` | dashboard only |
| Policy | residency/security rejections | `inv63_errors_total{code="INV63-E-POLICY"}` | `INV63PolicyRejections` — ticket |
| Control plane | lattice unreachable | `inv63_control_plane_up == 0` | `INV63ControlPlaneDown` — SEV2, page |
| Convergence | stalled workloads | `inv63_stalled_workloads > 0` | `INV63Stalled` — SEV2, page |
| Security | auth/replay/tenant/artifact/stale epoch | `inv63_alerts_total{cls="security_event"}` | `INV63SecurityEvents` — SEV2, page |
| Latency | request latency | `inv63_request_latency_ms` histogram | dashboard "p50/p95/p99 latency"; no alert (open) |
| Journal size | bytes vs J_max | **no metric emitted** | open item: add `journal_bytes` gauge + alert at 80% to trigger `compact()` |
| Pending offline intents | `status().degraded`, `len(pending)` | **no metric emitted** | open item |

Capacity numbers are not approved; fleet-scale validation (evidence `fleet-scale`) has not been run.
