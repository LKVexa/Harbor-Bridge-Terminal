# Operations runbook — INV-37 v4.3.0

Detailed policy lives in OPERATIONS.md (SLOs, rollout, incidents), CONFIGURATION.md (bootstrap) and FAILURE_MODES.md.

## Day 0 — bootstrap
1. Install the wheel; verify `health()["version"] == "4.3.0"` and record `artifact_digest`.
2. Create state dir (0700) and key ring (0600) from the secret manager.
3. `python tools/bootstrap.py --profile config/profiles/prod.json --site <site.json> --key-file <keys> --state-dir <dir> --dry-run`, fix any fatal finding, then run without `--dry-run`.
4. Run `python tools/run_certification.py` and `python conformance/run.py` on the target host; any `FAIL_REQUIRED_SKIPPED` blocks.
5. Run `python tools/production_gate.py --run --config-digest <digest>`. Do not promote on NO_GO without approved waivers.

## Day 1 — deploy
Canary → staged rollout per OPERATIONS.md §C092. Watch `observability/alerts.json` signals.

## Day 2 — operate
- Call `sweep()` on a timer (≤ `timeouts.idle_chunk`/2) to detect stalls and enforce total timeouts.
- Call `CheckpointStore.gc(retention_seconds=…)` daily.
- Inspect stranded transfers: `store.export_inventory()`; resume via `reconcile`; delete via `store.delete(tid)`; quarantine via `quarantine`.
- Rotate keys: add new key to ring file, `rotate()`, wait > token TTL, `revoke(old)`.
- Config change: build → `dry_run` → `activate(health_check=…)`; rollback with `ConfigManager.rollback()`.

## Rollback
`freeze(admin, True)` → drain → previous wheel → config rollback if needed → `recover()` → unfreeze. Checkpoint format is stable in 4.x.

## Emergency disable
`freeze(admin, True)`; tenant-scoped: `quarantine_tenant(admin, tenant)`. Both are audited and reversible.

## Incident
<a id="incident"></a>Integrity or cross-tenant suspicion = SEV1: freeze, quarantine, preserve `checkpoint.directory/quarantine`, audit log (verify with `security.verify_audit`), config history and gate report; rotate/revoke keys if compromise is possible; escalate per `governance/OWNERS.json`.
