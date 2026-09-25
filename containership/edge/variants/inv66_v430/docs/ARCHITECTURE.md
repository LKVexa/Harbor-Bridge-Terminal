# INV-66 architecture: topology, source of truth, lifecycle, capacity, degraded modes

Document ID `INV66-ARCH` · v1.0.0 · 2026-09-22 · normative for 4.3.x · owner: service owner · changes via PR + architecture review.
Covers MC-004, MC-005, MC-008, MC-009, MC-010, MC-040, MC-047, MC-048.

## 1. Deployment topology (MC-004)

```
            IdP (OIDC/SAML → JWT issuer)        GAP-13 policy engine        GAP-07 signing / transparency
                       │ tokens                        │ HTTPS mTLS               │ public keys (config)
 CI / GitOps / humans ─┼──► [ INV-66 leader  ] ──────► │                          │
   (HTTPS + bearer,    │    [ INV-66 standby ] (readyz=503 until lease)            │
    optional mTLS)     │         │ fsync journal on replicated volume ──► WORM anchor sink (object lock)
                       │         ▼
                       └──► INV-63 deployment manager(s) per lattice (accept only INV-66's client cert)
```

* **Unit of deployment:** one INV-66 *site instance* per (environment, site). Each owns one store directory. There is no global singleton (contract boundary "site").
* **Trust zones:** (Z1) callers — untrusted until token verified; (Z2) INV-66 process + store volume — trusted, holds anchor MAC key; (Z3) dependencies — authenticated by mTLS; (Z4) WORM sink — append-only, separate credentials, separate failure domain.
* **Failure domains:** node, store volume, site network, IdP, GAP-13, INV-63, WORM sink. Each has a defined behaviour in §5.
* **Endpoints:** `:8466` HTTPS API; `/healthz /readyz /version /metrics` bound to the ops network.
* **Standbys:** same store path on a synchronously replicated volume (or shared FS with POSIX `flock`); promote by lease expiry (`lease_ttl_s`, default 10 s). Split brain is prevented by the fencing epoch in every journal record: a stale leader's append fails `NOT_LEADER`.

## 2. Source of truth and consistency model (MC-005)

* The **journal** (`store.JournalStore`) is authoritative. Every decision, lifecycle transition, freeze, configuration activation, delivery result and export is an entry. In-memory state is a deterministic reduction (`service._apply`) and is rebuilt by replay at start-up.
* **Write-ahead rule:** an entry is fsync'd before its effect becomes visible; a delivery to INV-63 is attempted only after the `admission` entry with `admitted: true` is durable.
* **Consistency:** single writer per store → linearizable admissions within a site. Reads (`inventory`, `explain`, `audit`) are served from the leader and reflect every acknowledged write. Cross-site views are eventually consistent via audit export (MC-070).
* **Integrity:** SHA-256 chain with domain separation, per-record sequence and epoch; HMAC-signed snapshots; HMAC anchors published to an external WORM sink (MC-035).
* **Retention:** active journal is sealed into read-only archive segments when it reaches `audit_retention_records`; the snapshot carries reducer state. Purging archives requires no legal hold and updates the retention floor.

## 3. Decision lifecycle (MC-008)

`proposed → admitted | rejected`; `admitted → delivering → deployed | delivery_failed`; `delivery_failed → delivering`; `admitted/delivering/deployed/delivery_failed → quarantined`; `quarantined → admitted (requeue) | rolled_back`; `deployed → rolled_back`. `rejected` and `rolled_back` are terminal. Source: `lifecycle.py`; illegal transitions raise `ILLEGAL_TRANSITION` and are not journalled; operator transitions require `lifecycle.transition` on the decision's lattice. Rolling back removes the decision's components from inventory.

## 4. Capacity, quota, fairness and saturation (MC-009, MC-047)

| Quantity | Mechanism | Default |
|---|---|---|
| Concurrent admissions | `Bulkhead(max_inflight)` → `OVERLOADED` (fail fast, no unbounded queue) | 256 |
| Per tenant/lattice rate | `TokenBucket` quotas (`quotas` in config; key `tenant/lattice`, then `tenant`, then `*`) → `QUOTA_EXCEEDED` (retryable) | none unless configured |
| Manifest size / components | `max_manifest_bytes`, `max_components` | 1 MB / 256 |
| Request nesting | iterative probe | 32 levels |
| In-memory journal | compaction at `audit_retention_records` (maintenance loop), inline at 2× | 100 000 |
| In-memory decisions | terminal decisions pruned beyond 20 000; served from journal on demand | 20 000 |
| Replay cache (jti) | TTL-bounded, hard cap 100 000 → `OVERLOADED` | 100 000 |

**Measured (perf/results.json, fsync on, reference container, 2026-09-22):** sequential p50 1.8 ms, p99 3.9 ms, max 146 ms (compaction/fsync outlier); ~440 admissions/s single writer; 8-thread saturation p99 165 ms (queueing on the single writer — keep offered load ≤ 70 % of measured throughput); replay ~48 ms per 10 k records; ~665 journal bytes per admission; steady-state RSS growth 7 MB per 10 k admissions (TTL caches).

**Capacity formula:** safe QPS per site ≈ 0.7 × measured single-writer throughput on the target host. Journal growth/day ≈ QPS × 86 400 × 665 B. Scale thresholds: alert when `inv66_inflight / max_inflight > 0.8` for 5 min, or `rate(inv66_admissions_total{outcome="OVERLOADED"})` > 0.

Fairness: quotas are per tenant/lattice and the bulkhead is shared; a noisy tenant exhausts only its own token bucket. Weighted fair queuing is not implemented (waiver W-009).

## 5. Offline / partition / degraded semantics (MC-010, MC-040)

| Dependency down | Admission | Other operations | Signal |
|---|---|---|---|
| Identity issuer / JWKS | Tokens already configured keep verifying (keys are local config); new keys cannot be learnt | unchanged | `inv66_authn_failures_total` |
| GAP-13 policy engine | **fail closed**: decision recorded as rejected with `POLICY_UNAVAILABLE` (retryable); breaker opens after 5 failures, half-open after 30 s | reads OK | readiness `dependencies.policy-engine=degraded`, breaker state |
| Registry / transparency log | Verification uses pinned digests + configured keys, so registry outage does not affect admission; transparency adapter failure → `SIGNATURE_INVALID` (fail closed) | — | — |
| INV-63 deployment manager | Admission still decided and journalled; delivery → `delivery_failed`, retried from the outbox by `drain_outbox` / maintenance | — | `inv66_outbox_depth`, `inv66_deliveries_total{outcome="failed"}` |
| Store (disk full, I/O error) | **fail closed** `STORE_UNAVAILABLE`; nothing delivered | readiness false | `inv66_store_failures_total` |
| Lease lost / partitioned leader | `NOT_LEADER`; writes fenced by epoch | reads from stale memory are marked non-ready | `inv66_leader=0` |
| WORM anchor sink | Admission continues; anchoring retried each maintenance tick; alert after 15 min without an anchor | — | `inv66_audit_anchor_sequence` stale |

No degraded mode ever admits without authentication, authorization, provenance and policy.

## 6. Edge power/thermal (MC-048)

INV-66 is a central control-plane component; it is **not supported on constrained edge nodes** (C068 does not apply to its placement). This is an explicit unsupported mode, recorded as waiver W-012 (N/A with justification). If an edge placement is ever required, characterise with `tools/bench.py --soak-seconds 3600` under the target power governor and record watts/°C alongside the results.
