# GAP-01 Operator Runbooks

All commands assume the control socket `/run/gap01/control.sock` and an operator key. Requests are built with `gap01_edge_node_supervisor.client.make_request` (see `examples/sequences/`).

## Day 0 — bootstrap

1. Install package and `deploy/systemd/*` (unit, sysusers, tmpfiles). `systemd-sysusers && systemd-tmpfiles --create`.
2. Provision keys (≥32 random bytes each, mode 0600, owner `gap01`): `node.key`, `config.key`, `control-plane.key`, `health.key`, `operator.key`, (optional) `break-glass.key` stored offline.
3. Write `/etc/gap01/config.json` from `deploy/config/config.example.json`, sign with `tools/sign_config.py`. Install `signals.json`.
4. `systemctl enable --now gap01-supervisor`. Expect `READY=1`; `curl -s localhost:9101/livez` → 200.
5. Archive `/var/lib/gap01/boot_attestation.json` and the first `audit.jsonl` head hash as the baseline.
6. If boot fails the process exits 3 with `recovery_mode` and `failed_phase` on stderr (journalctl). Fix the phase and restart.

## Day 1 — deployment/rollout

Canary 1 node → 5 % → 25 % → 100 %, holding each stage ≥ 1 h with no page-severity alerts. Gate each stage on `tools/exit_gate.py` for the artifact and on SLO report (`diagnostics.slo`). Rollback: reinstall previous package; state schema is forward-migrated only, so restore the pre-upgrade backup when rolling back across a schema change (RB-12).

## Day 2 — operation

Re-run `tools/evidence.py` on every change; verify the audit chain (`python -c "from gap01_edge_node_supervisor.store import AuditLog;print(AuditLog.verify('/var/lib/gap01/audit.jsonl'))"`) weekly; rotate keys quarterly (RB-08).

## Incident severity

| Sev | Definition | Page | Examples |
|---|---|---|---|
| SEV1 | node stopped with residents, illegal transition applied, audit chain broken | immediate | SLO no-budget violation |
| SEV2 | emergency mode, watchdog hang, persistence errors, auth attack | immediate | alerts with `severity: page` |
| SEV3 | stuck drain inside grace, cordon ack overdue, pressure, throttling | ticket (business hours) | `severity: ticket` |

Escalation: on-call → component owner (OWNERS.md) → platform security (for T-series threats).

## RB-01 Cordon a node
`op=cordon args={"reason": "..."}` → note `result.cordon.generation`; expect the scheduler to send `cordon_ack` with that generation within `cordon_ack_timeout_s`.

## RB-02 Drain a node
`op=drain args={"timeout_s": N}`. Poll `status`. Node reaches `stopped` only with every reclaim proven.

## RB-03 Stuck drain {#rb-03-stuck-drain}
1. `status.drain` and `diagnostics.breaches` show remaining workloads. 2. If `unproven_reclaim` is non-empty the runtime reports exit but not release: inspect runtime resources; do **not** override until released. 3. Otherwise `drain_override {"extend_s": N}` or `{"force_now": true}` (operator). 4. If force-kill fails, escalate SEV2: the node stays `draining` by design.

## RB-04 Cordon acknowledgement overdue {#rb-04-cordon-ack}
Placement has not confirmed it stopped scheduling. Check scheduler connectivity; admission is refused locally regardless, so the risk is failed placements elsewhere, not unsafe placement here.

## RB-05 Emergency mode {#rb-05-emergency-mode}
`status.emergency.reason` names the trigger (autonomy expiry, watchdog, persistence failure, operator). Resolve the cause, then `emergency_exit` (operator) and `uncordon` once healthy.

## RB-06 Watchdog / probe down {#rb-06-watchdog}
systemd restarts the service when `WATCHDOG=1` stops. After restart the node is `cordoned` (R-LC-4). Collect `diagnostics` before uncordoning.

## RB-07 Resource pressure {#rb-07-pressure}
`diagnostics.pressure.reasons`. Free memory/disk or drain; admission resumes automatically when pressure clears.

## RB-08 Authentication failures and key rotation {#rb-08-auth}
Check audit `denied` events for caller identity. Rotate: write new key file, restart supervisor with the new `--caller-key`, update caller, remove old key. Suspected compromise → `emergency_enter` via break-glass.

## RB-09 Persistence errors / corrupt state {#rb-09-persistence}
Free disk; supervisor stays in emergency. For `E_STATE_CORRUPT`: stop service, `StateStore.restore(<latest backup>, /var/lib/gap01)`, start; reconciliation terminates orphans.

## RB-10 Throttling {#rb-10-throttling}
Compare `code="E_RATE_LIMITED"` by caller in audit/logs. Ordinary load → raise `rate_burst` via `reload_config`. Single misbehaving caller → fix caller.

## RB-11 Latency {#rb-11-latency}
Check fsync latency of the state volume; compare with `evidence/bench.json` baseline.

## RB-12 Backup and restore
Backup: `StateStore('/var/lib/gap01').backup('/backup/gap01-$(date +%F).tgz')` (daily and before upgrades). Restore: stop, restore, start. Restores reject unexpected archive members.

## RB-13 Emergency disable
`disable {"reason": ...}` (break-glass) writes `/var/lib/gap01/DISABLED`; systemd `ConditionPathExists=!` prevents restart. Re-enable: remove the file after review, start the service.
