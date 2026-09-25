# INV-31 Runbooks (C040, C092, C096, C097)

## Day 0 — bootstrap from an empty environment
1. `python3 -m venv .venv && . .venv/bin/activate`
2. `pip install .` (no third-party runtime dependencies)
3. `sh ci.sh` — must print `CI PASS`.
4. Provide signing keys and a `PK_INV31_CONFIG/1` document from the control plane.
5. Check `Gateway.health(now)["ready"] is True`.

## Day 1 — deploy
Canary one site with the new version; watch `errors.*`, warm rate, p99. Promote per site.
Rollback = redeploy the previous package; instances are never carried across versions,
so rollback is cold but safe.

## Day 2 — operate
* Config change: `ConfigManager.apply` (human/operator only); failure of the
  post-activation check rolls back automatically; `ConfigManager.rollback` for manual.
* Drain a tenant/version: `Gateway.drain` (needs `pool:drain`).
* Emergency disable: `Gateway.emergency_disable(reason=...)` → all invokes return
  `INV31-E-DRAINING`; `Gateway.enable` to restore. Both are audited.

## Incidents (C097) — template, escalation contacts UNASSIGNED
| Sev | Example | Response |
|---|---|---|
| 1 | any cross-tenant reuse; audit chain verify false | emergency disable, page owner + security |
| 2 | critical dependency down; error rate > 5 % | page owner |
| 3 | warm rate < 80 %; telemetry drops | ticket |
Containment first (disable/drain), then evidence (export audit chain + logs), then recovery.
