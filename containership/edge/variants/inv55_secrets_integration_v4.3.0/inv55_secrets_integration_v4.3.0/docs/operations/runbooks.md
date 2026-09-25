# Runbooks (day 0 / 1 / 2)

| ID | INV55-OPS-RUNBOOK | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: operations-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Day 0 — bootstrap
1. Provision Vault 1.15–1.18, KV v2 mount (default `secret`), per-tenant paths `<tenant>/<name>`, and INV-55's Vault policy (identity-roles.md).
2. Configure AppRole or Kubernetes auth for INV-55. Never put `secret_id`/tokens in config (`_CREDENTIAL_KEYS` rejects them).
3. Place CA bundle; build `build_tls_context(ca_file=...)`.
4. Write `config/base.json` + `config/overlays/<env>.json` (+ `<env>.<site>.json`); activate with `ConfigController.activate(load_layers(...))`. Record `provenance()` digest.
5. Create `FileAuditSink(path)` on a dedicated volume (mode 0600) and an HMAC key for `AuditChain` from key custody `<UNASSIGNED: key-custodian>`.
6. Run `python -m inv55_secrets_integration.bootstrap --config-dir config --env <env> [--site <site>] --check` to validate config, then without `--check` to start (`bootstrap.py`). Credentials are supplied as `file:`/`env:` references only; memory provider and static token are refused in `prod`. Exit code 0 = ready/degraded, 2 = otherwise.
7. Load policy rules (`PolicyEngine.replace`; bootstrap starts with an empty, deny-all policy) and apply scopes with `set_scope`. Scopes/retirements persist in `<audit path>.state.json` (write-ahead: an INTERNAL response means nothing was applied; retry).

## Day 1 — deploy
1. Roll out per rollout-rollback.md.
2. Check `health()`: `ready`, `state`, `version == 4.3.0`, `config.digest`, `policy_digest`, provider `reachable`, `sealed=false`, no `unsupported_server_version`.
3. Confirm scopes reloaded from the state file (crash-restart-semantics.md); re-load policy rules.
4. Smoke: resolve+use a canary secret via a canary workload identity.

## Day 2 — operate
- Rotation: `rotate` with `idempotency_key` and `expected_version`.
- Retirement: `retire`; persisted per instance; use `destroy=true` if the version must never be served anywhere.
- Backup: `export_state()` / copy state file and audit file (backup-restore.md).
- Policy change: always via `PolicyEngine.replace(rules)`; mutating `.rules` directly is unsupported (cached digest/index would be stale).
- Scaling: add processes (one per core) or instances, not threads (performance-policy.md).
- Config change: `activate`; on problems `rollback(1)`.
- Freeze: `freeze(operator_token, reason)`; unfreeze: `unfreeze(operator_token)`. The token MUST carry role `operator` and tenant `platform`; every attempt is audited.
- Audit verification: at every boot (automatic) and daily `audit.verify_chain(open(path,'rb'), hmac_key)`; on failure follow incident-response.md §3.
- Vault upgrade: confirm new version is in `SUPPORTED_SERVER_VERSIONS` first.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Platform operator requirement |
| 4.3.0 | 2026-09-23 | Write-ahead note, replace(), scaling |
| 4.3.0 | 2026-09-22 | bootstrap.py, state file |
