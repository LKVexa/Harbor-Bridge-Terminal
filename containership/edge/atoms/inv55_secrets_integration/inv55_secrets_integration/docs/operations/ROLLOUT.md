# Canary / staged rollout / rollback (checklist #91, DRAFT; automation BLOCKED on a deployment platform)

Stages: 1 % canary (1 site) → 10 % → 50 % → 100 %, minimum 30 min per stage.
Promote only if, over the stage window: `ready=true` on all canaries; denial rate within ±10 % of baseline; zero `internal_errors`; zero audit verification failures; resolve p99 within 1.5× baseline; no new SEV alert.
Automatic rollback triggers: any `internal_errors`, audit verification failure, `ready=false` > 2 min, or error budget burn > 10× (see SLO_POLICY.md). Rollback = previous artifact digest + `ConfigController.rollback`, recorded as provenance.
No deployment platform is available in this repository, so this is policy only (W-007).
