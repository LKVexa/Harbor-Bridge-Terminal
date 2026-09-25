# Operations runbooks — `DOC-INV52-OPS` v4.3.0 (C040, C092, C095-C097)

Status: PROPOSED. **No runbook here has been executed by an operator other than its author** (checklist exit criterion open).

## 1. Day 0 — bootstrap
1. Verify artifact: `python verify_integrity.py` (exit 0) and SBOM digest matches the release record.
2. Stage config layers (base, env, site); run `python -m inv52_messaging_abstraction config-check base.json env.json site.json` (exit 0 = valid).
3. Confirm dependencies: token key provider, clock, Dapr sidecar `GET /v1.0/healthz` (204), broker component loaded.
4. `lifecycle.bootstrap(layers, author=<you>, dependencies=...)` → state must be READY; otherwise stop (CONFIGURED means a critical dependency failed).
5. Record provenance digest in the change record.

## 2. Day 1 — deploy / canary / staged rollout
1. Release gate: `python -m inv52_messaging_abstraction gate` must report engineering PASS; production requires GO.
2. Canary: one site, 5 % of publishers for 30 min. Abort if any of: `classify()` ≠ normal_load/policy_rejection, p99 publish > baseline ×1.5, dead-letter rate > 2× previous release, any `software_defect`.
3. Stage: 25 % → 50 % → 100 % sites with the same abort criteria, 30 min each.
4. Rollback: `ConfigManager.rollback(author, reason)` for config; redeploy previous artifact digest for code.

## 3. Day 2 — operate
* Every config/runtime change: re-run tests + gate; keep the previous generation for rollback.
* Weekly: review `dead_letter_reasons`, shed counts per app (fairness), decision samples via `explain`.
* Key rotation: add new key id, switch `active_key_id`, wait ≥ max TTL (3600 s), remove old key.

## 4. Emergency disable
`ManagedBus.emergency_disable(actor, reason)` (component) or `set_topic_state(topic, "DISABLED"|"QUARANTINED"|"FROZEN")`. Choose FROZEN when publishers should retry later, QUARANTINED to keep accepting but hold messages, DISABLED to refuse. Record the incident id as `reason`.

## 5. Backup, restore, migration, reconstruction (C095)
INV-52 state is reconstructible: config generations (store in the config repo; restore = activate), subscriptions (re-created by applications at start), in-memory dead letters (**volatile** — export them with `bus.dead_letter` before planned restarts; durable DLQ is INV-53). Broker data backup/restore belongs to INV-54 owners. Migration between config majors: none exist yet.

## 6. Incidents (C097)

| Sev | Definition | Page | Ack | Escalate |
|---|---|---|---|---|
| SEV1 | cross-tenant exposure, auth bypass, silent loss, all publishes failing | on-call + security owner | 5 min | owner 15 min, exec 60 min |
| SEV2 | one site/topic down, overload shedding > 5 % for 15 min, dependency failure | on-call | 15 min | owner 60 min |
| SEV3 | degraded, elevated dead letters, single consumer broken | ticket | next business day | — |

Containment: quarantine or disable the topic; revoke capability (`TenantBus.grant(tenant, app)` with none); rotate keys on suspected token compromise. Recovery: fix → canary → unfreeze; verify audit chain (`AuditChain.verify(events, head=recorded_head)`). Post-incident: add a regression test and update THREAT_MODEL.md.

Roles for paging are `governance/owners.json` roles — all UNASSIGNED; paging cannot work until they are named.
