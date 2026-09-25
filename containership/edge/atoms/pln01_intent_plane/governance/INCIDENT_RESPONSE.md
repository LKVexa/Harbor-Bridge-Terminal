# Incident response model (MC-046)
Roles: Incident Commander (on-call primary) · Ops lead · Comms · Scribe · Security lead (for T-class threats).
Flow: detect (alert/report) → declare SEV → stabilise (freeze/quarantine/disable, never data edits) → diagnose
(explain(), audit.jsonl, traces) → recover (runbook) → verify (store.verify, gates) → close → blameless review within
5 business days with action items tracked in `governance/WAIVERS.json` (debt) or issues.
Evidence to preserve: state_dir copy, audit chain head, metrics snapshot, gate JSON of running release.
