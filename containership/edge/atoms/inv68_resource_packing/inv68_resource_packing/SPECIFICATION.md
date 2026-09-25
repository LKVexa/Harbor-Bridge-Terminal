# INV-68 Resource packing — Requirements specification 4.3.0

Normative language per RFC 2119. Each requirement has an ID used by
`REQUIREMENTS_TRACEABILITY.md` and `evidence/REQUIREMENTS_MATRIX.json`
(MC-05; INV-68-C005, C011–C020).

## 1. Functional requirements (C011)

| ID | Requirement | Verified by |
|---|---|---|
| REQ-F01 | The packer SHALL place each workload on the first open host, in dominant-share-decreasing order (ties by name), on which *every* dimension fits after headroom and overcommit. | `test_v43::test_MC22_differential_against_420_reference`, FUZZ reference oracle |
| REQ-F02 | The packer SHALL NOT place memory above `mem × (1 − headroom)` on any host. | FUZZ, SOAK, FAULTS F04, `test_headroom_and_no_memory_overcommit` |
| REQ-F03 | CPU SHALL NOT exceed `cpu × cpu_overcommit × (1 − headroom)`; `cpu_overcommit ∈ [1, 4]`. | `test_MC10_configurable_cpu_overcommit_memory_fixed`, FUZZ |
| REQ-F04 | A workload exceeding the effective capacity of an empty host SHALL be returned unplaced with reason `request_exceeds_effective_host_capacity` and the violated dimension(s). | `test_MC27_explain_view` |
| REQ-F05 | Every workload SHALL receive exactly one decision; `assignments` SHALL equal the placed decisions. | FUZZ oracle |
| REQ-F06 | Output SHALL be deterministic and invariant under input permutation. | FUZZ permutation oracle, `test_deterministic_order_for_equal_dominant_share` |
| REQ-F07 | Inputs SHALL NOT be mutated. | `test_does_not_mutate_caller_workloads`, FUZZ |
| REQ-F08 | Malformed, negative, boolean, non-finite and duplicate-named input SHALL be refused with `TypeError`/`ValueError` (engine) or `INVALID_REQUEST` (service); no other exception type may escape. | `test_malformed_workloads_rejected`, FUZZ (0 findings) |
| REQ-F09 | The service SHALL report capacity (`PK_PACK_CAPACITY/1`), fragmentation (`PK_PACK_FRAG/1`), the placeable lower bound and an explain view with every response. | SCHEMAS live checks |
| REQ-F10 | Fragmentation SHALL be reported, and impossible host accounting SHALL be refused. | `test_fragmentation_rejects_invalid_host_accounting` |

## 2. Assumption matrix (C005)

| Area | Assumption | Consequence if false |
|---|---|---|
| Nodes | Hosts within one request are homogeneous (same cpu, mem). | Caller must split by host class. |
| Nodes | Capacity figures are *allocatable* (after system reservations), in cores and GiB. | Headroom double-counts or under-counts. |
| Runtimes | Wasm/container runtimes enforce memory limits at the requested value. | Overcommit happens below INV-68; F02 cannot protect it. |
| Networks | The capacity source can be unreachable; the service never packs on data older than `capacity_staleness_s`. | STALE_CAPACITY/CIRCUIT_OPEN refusals. |
| Storage | The state directory supports fsync and atomic rename (preflight P05). | Activation atomicity lost. |
| Control planes | One INV-68 instance per site owns packing for that site; controllers carry a monotonic epoch. | Stale controllers are fenced (STALE_EPOCH). |
| Accelerators | Accelerator requests are handled by INV-72 before INV-68. | Workload would be packed without its GPU. |
| Time | Hosts are NTP-synchronised within ±30 s; token `iat/exp` and capacity `observed_at` rely on it. | Tokens/capacity refused as skewed (fail closed). |
| Wasm runtime | Declared requests are the runtime's hard memory limits (linear-memory max) and CPU shares. | Placement is correct on paper but not enforced. |

## 3. Deployment context profiles (C012)

| Profile | Applies | Recommended config | Notes |
|---|---|---|---|
| cloud | yes | headroom 0.10, cpu 1.5, staleness 60 s | capacity from provider inventory |
| datacenter | yes | headroom 0.10–0.15, cpu 1.5 | failover headroom sized to N+1 |
| near-edge | yes | headroom 0.15, cpu 1.25, staleness 120 s | smaller hosts: fragmentation matters more |
| far-edge | yes, degraded | headroom 0.20, cpu 1.0, staleness 600 s, max_concurrency 2 | disconnected operation §8; power by GAP-10 |

Profiles are overlays (`config.compose`, `environment:` / `site:` layers).

## 4. Non-functional requirements (C013)

| ID | Class | Requirement |
|---|---|---|
| NFR-01 | latency | p99 < 100 ms for 1000 workloads (engine), measured per release. |
| NFR-02 | efficiency | hosts ≤ 1.10 × placeable lower bound in ≥ 95 % of batches. |
| NFR-03 | availability | the service SHALL be ready whenever a verified configuration is active and not frozen; target 99.9 % monthly (proposed, needs owner). |
| NFR-04 | durability | a committed configuration activation SHALL survive process crash and power loss (fsync + atomic rename). |
| NFR-05 | consistency | one active configuration digest per instance at any instant; activation is CAS on the digest plus epoch. |
| NFR-06 | isolation | a principal SHALL only pack for tenants in its scope; results never mix tenants. |
| NFR-07 | determinism | identical (request, config digest, capacity) → byte-identical `result`. |
| NFR-08 | bounded resources | payload ≤ `max_payload_bytes`, workloads ≤ `max_workloads`, in-flight ≤ `max_concurrency`, queue ≤ `max_queue`. |

### SLI definitions (MC-33)

| SLO | SLI | Population | Window | Method |
|---|---|---|---|---|
| no memory overcommit | `inv68_mem_overcommit_hosts` > 0 events | every successful pack | 30-day rolling | count; budget 0 |
| efficiency | batches with `hosts / placeable LB ≤ 1.10` | successful packs with ≥ 1 placed workload | 30-day rolling | ratio of good batches |
| pack time | `inv68_request_latency_ms` for requests of ≤ 1000 workloads | successful requests; excludes caller-cancelled and refused (4xx-class) | 30-day rolling | p99 from histogram buckets (linear interpolation) |

## 5. Outcome model (C014)

`success` (all placed) · `partial` (some unplaced; response still valid) ·
`degraded` (served while a dependency/audit is impaired — visible in status) ·
`retryable` / `refused` / `terminal` errors per `ERRORS.json`. Every error carries
`retryable`, a status code and a correlation id.

## 6. Lifecycle (C015)

```
            activate(valid cfg)                    freeze (operator, audited)
NOT_READY ─────────────────────▶ READY(ok) ─────────────────────────────▶ FROZEN
    ▲                              │   ▲  ▲                                   │
    │ no intact config             │   │  └──────── unfreeze (audited) ───────┘
    │                              ▼   │
    └──────── (never) ──────── DEGRADED (breaker open | stall | audit buffered | recovered config)
```
Legal transitions only as drawn; FROZEN persists across restarts; activation and
rollback are allowed in READY, DEGRADED and FROZEN (so a fix can be staged while frozen).

## 7. Compatibility policy (C016)

Semantic versioning. Minor releases add optional fields only; `PK_PACK/1` requests
from 4.2.0 remain valid. Removal requires a new protocol major (`PK_PACK/2`) with a
negotiation overlap of one minor release. Support window: `compatibility.json`.

## 8. Quotas and fairness (C017) · disconnected operation (C018)

Per-tenant `max_workloads_per_request` and `max_requests_per_minute` (sliding
window), defaults plus overrides; exceeding either yields `QUOTA_EXCEEDED`
(retryable). Admission is FIFO within `max_queue`; no tenant can occupy more than
one queue slot per request. Disconnected: with no fresh capacity, INV-68 refuses
(`STALE_CAPACITY`) rather than guessing; callers may pass `host_capacity`
explicitly (local knowledge) — that path keeps working offline.

**Reservation / priority / preemption:** not owned by INV-68 (contract non-goal).
There are no priority classes; admission is FIFO. A batch that cannot be fully placed
is returned `partial` with explained refusals — INV-68 never evicts placed work.

## 9. Conflict precedence (C019)

1. Security (authn/authz/tenant scope, secrets) — always wins.
2. Safety (no memory overcommit, headroom floor) — cannot be traded for density or SLO.
3. Residency/tenancy boundaries.
4. SLOs (latency, efficiency).
5. Cost/density.

Examples: a caller cannot lower headroom to fit more work (2 > 5); a frozen service
refuses even if that breaches the latency SLO (1/2 > 4).

## 10. Traceability (C020)

`REQUIREMENTS_TRACEABILITY.md` maps every INV-68-C### control and REQ id to code,
tests, schemas, evidence and owner role; the machine-readable form is regenerated by
`tools/build_ledger.py` into `evidence/REQUIREMENTS_MATRIX.json`.
