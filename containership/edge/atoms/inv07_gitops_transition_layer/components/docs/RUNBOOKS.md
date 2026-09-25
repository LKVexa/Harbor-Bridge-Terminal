# INV-07 incident runbooks

**Status:** DRAFT — not yet exercised by an operator; owner/on-call rota unassigned (`OWNERS.md`).

## Severity

| Sev | Definition | Page | Response |
|---|---|---|---|
| SEV1 | Unsigned/untrusted state applied, key compromise, cross-tenant write, partial apply on production | immediately | 15 min |
| SEV2 | Sync stalled > 3 intervals, no leader, drift recurring, git circuit open > 30 min | business hours + on-call | 1 h |
| SEV3 | Policy denials, log drops, queue saturation | ticket | next day |

Roles: incident commander, controller operator, security lead (SEV1), comms.

## inv07unsignedcommitrefused
1. `GET /v1/explain/<decision>` → signer, error code. 2. If `PKG-TRUST-002/003` on a legitimate change, the signer used an unenrolled or revoked key: re-sign, do **not** weaken trust roots. 3. If unexpected: treat as attempted compromise → SEV1, freeze the ref (`POST /v1/freeze {"scope":"ref"}`), preserve `audit.jsonl`, `explain.jsonl` and the mirror.

## Compromised signing key (SEV1)
1. Global freeze: `POST /v1/freeze {"scope":"global","name":"*","reason":"key compromise"}`. 2. Revoke in trust roots (`revoked_at` = now, `revocation_mode: hard`) and redeploy the trust file (immutable setting → restart). 3. List commits signed by the key since its enrolment (`git log --format='%H %G?'` on the mirror and audit `sync.accepted` entries). 4. Decide rollback target (last commit signed by a clean key) → signed revert by a clean key. 5. Release the freeze with `freeze.override` + second approver. 6. Seal and export the audit ledger; anchor the head externally.

## inv07partialapplyfrozen
1. The target is frozen automatically. 2. Read `explain` → failed resource + compensation errors. 3. Compare live vs last committed digests (`status`, journal). 4. Repair the target by hand **or** fix and re-sign desired state. 5. Release the freeze (operator who set it, or `freeze.override`).

## inv07syncstalled / inv07gitcircuitopen
Check `status.reasons`; `git ls-remote` from the controller host; offline mode decides behaviour (`fail_closed` default). Never switch to `cache_backed` during a trust incident.

## inv07noleader / inv07leaderchurn
Check lease directory/Lease object, clock skew (`time:` reasons), node restarts. Never delete the lease file while a node may be running.

## inv07driftreverted
Find the out-of-band writer (INV-05 audit, cluster audit log). Recurring drift → coordinate ownership or migration partition (`MIGRATION_FROM_IAC.md`).

## inv07convergencesloburn / inv07policydenials / inv07queuesaturated / inv07logdrops
Follow the alert annotation; policy denials are expected behaviour — fix the manifest or add a time-bounded, approved waiver.

## Rollback decision tree
Is the bad state signed & trusted? → yes: signed revert to the last good OID. → no: it was never applied (verify via `explain`). Is the target half-applied? → partial-apply runbook first.

## Evidence preservation
Copy `state/` (journal, audit, explain, freshness, freezes) and the mirror before any repair; record `sha256` of each file and the audit head.
