# Failure taxonomy (v4.3.0)

| Layer | Failure | Detection | INV-58 behaviour | Test |
|---|---|---|---|---|
| Component | invariant violation | defensive `RuntimeError` in reconcile | fail closed, `E_INTERNAL` class | fuzz invariants |
| Component | stall (in-flight work, no progress) | `health().stalled` after `health.stall_after_s` (30 s) | liveness false | `test_stall_detection` |
| Component | error burst | error ratio > `health.max_error_ratio` (0.5) over ≥ `min_samples` (20) | `health.error_burst` true → alert | `test_stall_detection` |
| Process | crash / restart | readiness absent | restore sealed snapshot; fencing refuses stale writers | restart tests |
| VM / node | node agent lost | missing bypass reports (RR-04) | nothing flagged; alert `NodeSilent` | — |
| Site | site loss | per-site instances | other sites unaffected (no global singleton) | — |
| Network | partition to trust services | dependency probe | fail closed / degraded per `trust_outage_policy` | partition tests |
| Provider | KMS outage | `SecretResolutionError` | token auth denied; mesh-identity data plane continues | key outage tests |
| Dependency | identity/policy/time/attestation down | `set_dependency` probes | fail closed, readiness false | outage tests |
| Dependency | audit sink down | probe | audited operations fail closed | audit sink test |
| Dependency | telemetry down | probe | degraded; data plane continues, mutation paused | degraded test |
| Control plane | stale/partitioned controller | fencing token | `E_STALE_FENCE`, audited | split-brain test |
| Control plane | bad config | validation / post-activation probe | not activated / auto-rolled back | config tests |
| Control plane | overload | admission | `E_OVERLOADED` shed, fair share | burst test |

## Thresholds
- Stall: in-flight > 0 and no completed operation for 30 s (configurable 1 s–1 day).
- Error burst: ratio > 0.5 over ≥ 20 samples.
- Breaker: open after 5 consecutive dependency failures, half-open after 30 s, 1 probe.
- Detection latency objective: dependency outage reflected in readiness on the next probe call (synchronous); false positives are bounded by requiring `min_samples` before an error-burst verdict.
