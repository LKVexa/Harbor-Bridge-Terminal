# Day-0 / day-1 / day-2 runbooks  (component 95)

## Day 0 — bootstrap (owner: accountable owner; rollback authority: same)
Preconditions: Python ≥ 3.10; for extras, network access to the package index.
1. `tools/bootstrap.sh` (creates venv, installs pinned extras requested, runs tests, writes evidence).
2. Validate config: `python -m inv54_broker_implementations validate-config config/base.json config/overlays/<site>.json` → expect `"valid": true`.
3. Hardening checklist: run as non-root; read-only root filesystem except `storage.path`; network egress only to provider endpoints; secrets mounted via the secret provider, never files in the repo.
Failure branch: validator problems → fix overlay; never bypass.

## Day 1 — deploy
1. Stage config: `ConfigStore.stage()` → `commit(expected_current=<current digest>)`; record provenance.
2. `BrokerService.start(config_digest)`; expect `health().ready == true`, `state == "ready"`.
3. Follow `ROLLOUT.md`.

## Day 2 — operate
- **Consumer lag / stall:** `health()["stalls"]` → restart consumer; if backlog near ceiling, raise limit via config or quarantine tenant.
- **Degraded:** read `degraded_reasons`; fix dependency; `reevaluate()`.
- **Config rollback:** `ConfigStore.rollback(author=...)`; verify digest equals previous known-good.
- **Retention:** schedule `DurableLog.apply_retention()`; alert on `INV54-E0204` for record ceiling.
- **Backup:** daily `DurableLog.backup()`; monthly restore drill into an empty directory, verify record counts.
- **Replica failover:** `ReplicatedPartition.failover()`; confirm fenced epoch increase and HW.
Evidence retention: keep generated `evidence/` per release ≥ 1 year.
