# Ownership and escalation

The authoritative machine-readable record is `ops/oncall.json` (roles, escalation chains, support boundary, approval authority, severity mapping, review cadence). This page explains how to use it; it does not duplicate names.

- **Find the owner during an outage:** the release zip and the day-0 bundle carry `ops/oncall.json`; roles resolve to people in the owner's directory, not here.
- **Every privileged action has an approving role** (`approvals` in the file); emergency controls always need a reason and ticket and are audited.
- **Stale-owner detection:** `tools/check_repo.py` fails when a role is missing, and `tools/gate.py` reports every `UNASSIGNED` role and a `last_reviewed` older than `review_cadence_days` as release blockers.
- **Response expectations:** SEV1 ack 15 min, mitigation 1 h; critical vulnerability triage 2 business days (see `SECURITY.md`).
- **Waivers and debt:** `pln05.waiver-owner` owns `governance/waivers.json`; expired waivers block release.
