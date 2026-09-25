# INV-68 incident response (MC-38; C097)

## Phases
1. **Detect** — alert (ops/alerts.json) or report; open an incident with id, severity (RUNBOOK §10), commander.
2. **Contain** — `freeze` if placements may be unsafe or wrong; revoke/rotate token kids for credential incidents; tighten quotas for abuse.
3. **Preserve evidence** — before any restart: copy `audit.jsonl` + anchor, `cfg/` (snapshots, journal, ACTIVE, FROZEN), recent structured logs, `status()` output, metrics snapshot. Run `inv68-audit verify` and record the result.
4. **Recover** — fix via config activation or release rollback; unfreeze; watch one bake period.
5. **Post-incident** — timeline from audit + logs (correlation ids), root cause, regression test/fuzz fixture, register entry if a waiver is needed, runbook update within 5 business days.

## Security
Signals: A04 (UNAUTHENTICATED/REPLAY spikes), unexpected `config.*`/`control.*` actors in
the audit ledger, chain verification failure. Actions: rotate the affected kid
(add new, re-issue, remove old), freeze if integrity is in doubt, notify security_owner
(UNASSIGNED) and the repository owner, follow SECURITY_RESPONSE.md for disclosure.

## Audit loss
Signal: A09 or an `audit.loss` record. Check the sink (disk full, permissions). Policy
changes are already refused while the sink is down (fail closed). After recovery,
verify the chain, seal a new anchor, and record the loss window in the incident.
