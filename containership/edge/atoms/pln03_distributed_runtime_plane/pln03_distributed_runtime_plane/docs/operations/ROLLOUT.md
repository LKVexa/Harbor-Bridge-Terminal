# Canary and staged rollout (MC-049)

| Stage | Scope | Min soak | Promote when | Abort when |
|---|---|---|---|---|
| 0 Pre-flight | CI | — | `tools/release_evidence.py` PASS, evidence sealed | any gate fails |
| 1 Canary | 1 site of each class, ≤ 1 % tenants | 1 h | error rate ≤ baseline + 0.1 pp; p99 within NFR-LAT-01; zero `deny` anomalies; audit chain verifies | any SEV1/SEV2 signal, breaker open, fencing conflict |
| 2 Early | 10 % sites | 24 h | same | same |
| 3 Broad | 50 % | 24 h | same | same |
| 4 Full | 100 % | — | — | — |

Rollback = redeploy previous release digest + `ConfigStore.rollback` to the paired config revision. Emergency disable = RB-01.
**Automation status:** criteria are machine-checkable from `/health` and metrics, but the promotion controller itself belongs to the deployment system (PLN-04/Wadm) and is not in this archive — MC-049 remains partially open.
