# Canary, staged rollout, rollback and emergency disable (C092)

Approval: **PENDING**.

## Preconditions (every stage)
`python verify.py` on the exact artifact: verdict `PASS` (production) — any
`PARTIAL`/`FAIL` blocks promotion. Evidence digest recorded in the change ticket.

## Stages

| Stage | Scope | Soak | Promote when | Automatic rollback trigger |
|---|---|---|---|---|
| 0 lab | 1 host, synthetic guests, `datacenter-lab` config | 24 h | zero page alerts; perf gate green | any page alert |
| 1 canary | 1 % hosts in 1 site, non-critical tenants | 48 h | SLO burn < 1×; no E1xx increase vs control | bounds/stall/security alert; burn > 2× |
| 2 site | 1 full site | 72 h | as above | as above |
| 3 region | 25 % → 50 % → 100 % hosts | 24 h each | as above | as above |
| 4 far-edge | far-edge profile fleet in waves of 10 % | 72 h first wave | offline-policy drill passed | as above |

## Rollback
* **Artifact:** redeploy previous release (its manifest/evidence is retained); queues drain (DRAINING→STOPPED) and re-register on the old version.
* **Configuration:** `ControlPlane.rollback_config(..., to_generation=N)` → `ConfigStore.rollback()` (history keeps 8 generations; rollback is itself a new generation with `rollback_of`).

## Emergency disable
* One queue: `transition(target=QUARANTINED)` (security hold, reversible only via DISABLED/STOPPED + re-create) or `DISABLED` (kill).
* Whole host: apply site override `{"queue_depth": 1, "submit_rate_per_s": 1.0, "submit_burst": 1.0}` (tighten-only fields accept this without a rebuild), then quarantine queues.
* Both actions are audited and journalled; they survive restart (recovery preserves QUARANTINED/DISABLED).

## Exercise
Canary + rollback must be exercised on each release candidate; record in `evidence/rollout-<ver>.json` (template in `evidence/README.md`).
