# INV-63 Service Level Objectives

| Field | Value |
|---|---|
| Document ID | INV63-GOV-SLO |
| INV-63 C-IDs covered | C091 |
| Status | DRAFT — pending approval (all targets PROPOSED) |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | SRE lead (role), Product/tenant representative (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or after any SEV1/SEV2 postmortem. |

## Contract SLOs (`contract.py::build`)
| SLO | Objective | Budget | Measurement |
|---|---|---|---|
| convergence | a second reconcile after convergence emits zero actions | no budget | tests; production: `inv63_reconciles_total{result="applied"}` immediately after a successful reconcile should be 0 (no dedicated SLI metric) |
| availability (rollout) | never more than `max_unavailable` instances down during rollout | no budget | `op_rollout` `worst_unavailable`; not an exported metric |
| reconcile time | p99 diff < 10 ms for 1000 instances | 1% may exceed | `perf/bench.py` `diff_1000_*`; not measured in production |

## Proposed service SLOs (30-day window)
| SLI | Target | Error budget | Source |
|---|---|---|---|
| API success: `requests_total{outcome in SUCCESS,PARTIAL,DEGRADED}` ÷ (requests + errors excluding client TERMINAL codes `INV63-E-SCHEMA`, `-INVALID-REQUEST`, `-FORBIDDEN`, `-UNAUTHENTICATED`, `-POLICY`, `-QUOTA`) | 99.9% | 0.1% of requests | `inv63_requests_total`, `inv63_errors_total` |
| Request latency p99 (`request_latency_ms`) excluding lattice time | < 50 ms | 1% | histogram |
| Convergence latency: desired change → CONVERGED | < 2 × `reconcile_interval_s` when lattice up | 1% | not instrumented — open |
| Readiness (`status().ready`) | 99.9% | | not exported as metric — open |
| Stalled workloads | 0 for > 10 min | alert `INV63Stalled` | `inv63_stalled_workloads` |

Far-edge: SLOs apply only while the lattice is reachable; offline periods within `offline_autonomy_s` count as DEGRADED (not failures).

## Support commitments (proposed)
Business-hours support for SEV3/4, 24×7 paging for SEV1/2 (see `ops/runbooks/INCIDENT.md`). On-call roles UNASSIGNED; no commitment is in force until the owner approves.

## Error-budget policy (proposed)
Budget exhausted → freeze non-emergency INV-63 releases until 7 days within budget; SEV1 → mandatory postmortem.
