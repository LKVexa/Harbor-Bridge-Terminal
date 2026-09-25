# Day 1 — routine operations

- **Health:** probe `health()` (liveness = `live`, readiness = `ready`); scrape metrics `exposition()`; watch the dashboards in `observability/dashboards.json`.
- **Config change:** dry-run first (`ConfigStore.dry_run` / CLI `validate-config`), review the diff, then `activate_config` with a platform_operator credential; confirm the new checksum in `status()`. Rollback: `rollback_config`.
- **Ceiling pressure** (`PLN05PersistentCeiling`): the workload is pinned at its declared ceiling. Raise it only via PLN-01 (new limits revision); never through PLN-05.
- **Key rotation:** add the new key with overlap ≥ 1 h, wait one token lifetime, revoke the old key after its window; verify `status(admin).keys`.
- **Release rollout:** follow `docs/release-policy.md` (rings, canary criteria, rollback triggers).
