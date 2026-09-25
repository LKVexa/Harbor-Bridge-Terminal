# Canary, staged rollout, rollback, emergency disable (MC-057)

1. **Pre-flight:** `python tools/production_gate.py --strict` must be GO for the exact archive digest.
2. **Canary (1 node / 1 site, 24 h):** activate new config revision via `ConfigStore.activate`; watch SLO dashboards; abort criteria: any device-model event, boot p99 > 125 ms, admission error ratio > 1 %, audit verify failure.
3. **Stage 10 % → 50 % → 100 %**, 24 h soak each, same abort criteria.
4. **Rollback:** `ConfigStore.rollback(author=…)` for config; redeploy previous sealed archive for code (previous gate result must still verify).
5. **Emergency disable:** `ControlPlane.freeze(operator, True, reason)` stops all new admissions within one request; `quarantine("node", …)` isolates a node; running guests follow `degraded_policy`.
6. Record every step as an audit event and attach gate output to the change ticket.

Exercise status: **NOT_EXERCISED** (requires staging fleet) — MC-057 BLOCKED.
