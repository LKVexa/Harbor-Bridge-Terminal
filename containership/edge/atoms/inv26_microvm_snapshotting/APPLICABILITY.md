# Deployment-tier applicability, precedence and residency (C012, C019)

Source of truth: `policy.py` → `ops/policy.json` (generated). Enforced in `SnapshotService._preamble`
before any side effect; unsupported combinations are **rejected** (`SNAP_TIER_UNSUPPORTED`), never
best-effort executed.

| Tier | capture | restore | delete | replicate | emergency disable | min kernel | KVM | TPM required | max KMS outage | restore p99 target |
|---|---|---|---|---|---|---|---|---|---|---|
| cloud | supported | supported | supported | prohibited | supported | 5.10 | yes | no | 0 s (fail closed) | 10 ms* |
| datacenter | supported | supported | supported | prohibited | supported | 5.10 | yes | no | 0 s | 10 ms* |
| near-edge | supported | supported | supported | prohibited | supported | 5.10 | yes | yes | 300 s** | 25 ms* |
| far-edge | degraded | supported | supported | prohibited | supported | 5.10 | yes | yes | 3600 s** | 50 ms* |

\* targets are PROPOSED and unmeasured on a real VMM (see BENCHMARKS.md). \** tolerated outage means the
tier can stay *ready* for already-captured snapshots only if a local KMS replica is present; this repository
has no such replica, so the implementation fails closed at 0 s in every tier (the stricter behaviour).

**Residency:** config `residency.allowed_sites` / `allowed_regions` must include the node's own site/region
(validated at activation) and every request's site must equal the node's site; a restore can never move
state to another site (`SNAP_RESIDENCY_VIOLATION`). Replication is prohibited in every tier.

## Precedence (lower wins)
1 isolation/security → 2 legal residency → 3 integrity/consistency → 4 operator safety → 5 SLO/availability →
6 cost. Encoded conflicts PC-01..PC-06 in `policy.CONFLICTS` with deterministic actions; tests in
`tests/test_service.py::Precedence` show SLO never overrides entropy or KMS, and the policy document is
versioned (`PK_SNAPSHOT_POLICY/1.0.0`) and recorded in every decision record.
