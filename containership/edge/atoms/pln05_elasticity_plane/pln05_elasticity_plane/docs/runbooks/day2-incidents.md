# Day 2 — incidents and recovery

Severity: **SEV1** targets wrong/unsafe or split brain, or all scopes unready; **SEV2** one site unready, decisions failing, audit sink down; **SEV3** stale demand for some scopes, noisy alerts. Paging and escalation: `ops/oncall.json`. Every incident: contain → recover → verify → postmortem within 5 business days (blameless, action items with owners in `governance/waivers.json` if debt is accepted).

## not-ready
`status().blockers` names the cause: `R_TIME_FAULT` (fix NTP; plane recovers when the clock passes its last value), `R_NO_ACTIVE_KEY` (load keys), `R_STATE_CORRUPT` (see backup-restore), `R_AUDIT_BUFFER_FULL` (restore audit sink), `R_STALLED` (capture stack, restart instance; lease hands over within 15 s), `R_DRAINING` (expected during shutdown).
## decision-failures
`E_INTERNAL` errors: freeze affected tenant (`control freeze`, reason + ticket), capture logs by `correlation_id`, roll back the release.
## stale-demand
Scope in stale/degraded: targets are held. Contact GAP-09 owner. Freeze if > 30 min to make the hold explicit.
## lease-loss
`E_NOT_LEADER` bursts: check coordination service; if another instance holds the scope this is normal failover.
## split-brain
`E_FENCED` means a stale instance tried to publish: stop that instance, confirm `status(admin)` epochs, verify downstream applied tokens are monotonic.
## audit-sink
Restore the sink; records buffer up to 256; at 75 % scale-up is refused, at 100 % audited actions and decisions are refused.
## provider-outage
Sink breaker open: decisions persist; after recovery run `republish_last` per scope (idempotent).
## security
`E_AUTHZ_SCOPE`/`E_AUTHN_*` spikes: quarantine the offending source (`control quarantine … source=`), rotate/revoke its credentials, open a security incident with `pln05.security-contact`.
## slo-burn
Multi-window burn: identify dominant error code on the dashboard, apply the matching section.
## emergency-controls
freeze (hold target, publish nothing) → quarantine (reject a source or scope) → disable (reject all decisions for a scope/tenant). Resume needs two different emergency_admin principals. Before resuming: demand fresh, `ready: true`, explain the last decision, confirm envelope with PLN-01.
