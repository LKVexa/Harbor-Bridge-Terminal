# Runbooks — day 0 / day 1 / day 2 (INV55-RB-001, DRAFT; staging exercise NOT yet performed)

Owner: UNASSIGNED · Review cadence: quarterly and after every SEV1/SEV2 · Paging: see `docs/governance/OWNERSHIP.md`.

## Day 0 — bootstrap
1. Provision trust roots as files readable only by the INV-55 UID: `INV55_VAULT_ROLE_ID_FILE`, `INV55_VAULT_SECRET_ID_FILE` (or `INV55_VAULT_TOKEN_FILE`), CA bundle at `provider.ca_file`.
2. Compose config: `deploy/config/production.example.json` + site overlay. Never place credential material in config (the controller refuses it).
3. Run `python -m inv55_secrets_integration.tools.bootstrap base.json overlay.json --author <you> --source <git-sha>`.
   Expected: five lines `[n] PASS …`, exit 0. **Decision point:** any FAIL → stop; exit code = failed step (1 config, 2 provider/trust root, 3 provider health/sealed, 4 audit sink, 5 readiness).
4. Commit config with a second person: `ConfigController.commit(approved_by=<other person>, require_approval=True)`.
5. Record the audit head externally (release evidence) — it is the truncation anchor.

## Day 1 — routine
* Health: `health.status(svc)`; alert when `ready=false` > 1 min (`deploy/monitoring/alerts.yaml`).
* Rotation: `ROTATE` with a fresh `idempotency_key` and `expected_version`; confirm new resolves get v+1, old leases continue until TTL; retire old version after max lease TTL (`retire(name, v)`).
* Renewal: Vault token renews automatically `renew_margin_s` before expiry (AppRole re-login); watch `inv55_failures_total{reason="unauthenticated"}`.
* Capacity: watch `inv55_denials_total{reason="quota"}`, bulkhead `overloaded`, lease table size (bench `saturation`).
* Deployments: canary per `ROLLOUT.md`.

## Day 2 — maintenance and emergencies
* **Upgrade:** deploy to canary; run `tools/ci.sh` evidence on the candidate; compare bench regression (`tools/bench.py` vs baseline, tolerance 1.5×). Rollback = previous artifact + `ConfigController.rollback`.
* **Provider sealed / outage:** breaker opens, `ready=false`, requests RETRYABLE. Do **not** enable stale serving in production without an approved waiver. Unseal is a Vault operator action (outside INV-55).
* **Failover:** reads move to replica automatically; writes stay failed until primary returns (by design). Failback after 30 s healthy.
* **Key/cert rotation:** rotate CA bundle by adding the new CA, deploying, then removing the old one; rotate IdP HMAC keys by adding a new `kid`, waiting max token lifetime (≤ 1 h), then removing the old key.
* **Backup/restore:** `BACKUP_RESTORE.md`.
* **Decommission:** freeze `global`; revoke outstanding leases (restart suffices — leases are memory-only); archive the audit file and its head; revoke the AppRole; remove policies.

Safety warnings: never paste a token into a ticket or chat; never run with `allow_insecure_loopback` outside test (config refuses it); never self-approve a config commit (controller refuses it).
