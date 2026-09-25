# Operations: canary, rollback, emergency control, incident runbook

## Canary (component 68)
1. Deploy to one instance group with `Limits` unchanged from the previous release.
2. Scrape `render_prometheus()` from baseline and canary for ≥ 30 min.
3. Run `python ops/rollback_hook.py baseline.prom canary.prom`; exit 2 = ROLLBACK, 0 = PROCEED.
4. Promote in 1% → 10% → 50% → 100% steps, re-running the hook at each step.
**Not exercised against a real fleet** — no fleet exists for this reference host.

## Rollback hook (component 69)
`ops/rollback_hook.py` compares canary to baseline: foreign-handle rate, refusal rate, late completions, memory refusals, release errors, cancel-ack p99. Thresholds are PROPOSED values in the script, unapproved.

## Emergency disable / drain (component 70)
- `host.disable()`: refuse every call (DISABLED), cancel all pending with EMERGENCY_DISABLE, audit record. `host.enable()` reverses.
- `host.drain(view, "allow"|"cancel"|"invalidate")` + `host.drain_progress(view)` for per-instance quiesce.
- Absence of the component MUST NOT be read as a passing gate (carried from v4.2).

## Incident runbook (component 71)
| Symptom | Check | Action |
|---|---|---|
| `pk_async_refusals_total{scope=…}` rising | `explain()` per-instance refusals | raise the named scope's limit or drain the hog instance |
| `pk_async_foreign_handle_total` > 0 | `audit.records` kinds `foreign_handle`/`tenant_mismatch`/`replay`; `audit.verify()` | treat as security incident; preserve audit chain head |
| stuck ready (`pk_async_subtasks_ready` flat & > 0) | scheduler adapter attached? (`explain().dependencies.scheduler_hooks`) | restart scheduler; readiness is retained in the table |
| memory near ceiling | `pk_async_memory_soft_limit_total`, `explain().process.memory_bytes` | lower payload sizes or raise `mem_*`; note declared row size understates real heap ~4.5x (see benchmark) |
| everything failing | `host.disable()` | then restart → new epoch invalidates all handles |
Untested in a live incident.
