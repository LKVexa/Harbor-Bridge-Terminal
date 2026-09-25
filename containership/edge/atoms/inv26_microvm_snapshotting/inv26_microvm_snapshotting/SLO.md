# SLOs, error budgets and support commitments (C091)

| SLO | Objective | Error budget | Measured by | Status |
|---|---|---|---|---|
| tenant binding | zero cross-tenant restores | none | `inv26_cross_tenant_refusals_total` (refusals), audit | enforced; refusal tests pass |
| entropy | zero restores without re-seed | none | READY only after ack; `inv26_reseeds_total` == READY count | enforced |
| restore time | p99 < 10 ms (contract) | 1 % | `inv26_restore_ms` | **UNMEASURED on a real VMM**; INV-26 overhead alone is ~3 ms p50 at 1 MiB and ~32 ms p50 at 16 MiB (BENCHMARKS.md) — the contract SLO is **not supportable for images ≥ ~4 MiB** with whole-image decryption; proposed per-class targets in APPLICABILITY.md |
| availability | 99.9 % successful (non-policy) requests / 30 d | 0.1 % | `inv26_requests_total` excluding policy/integrity rejections | proposed |

Support commitments (proposed, unapproved): SEV1 security response 24×7 once on-call exists; supported
versions = current + previous minor; see SECURITY_RESPONSE.md for patch SLAs.
