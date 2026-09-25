# Incident response runbook — INV-42 (MC-038)

## Severity

| Sev | Definition | Page | Update cadence |
|---|---|---|---|
| SEV1 | Confirmed forged/cross-table acceptance, key or signing-key compromise, tampered release | immediately, 24/7 | 30 min |
| SEV2 | Attack alert firing (`INV42SecurityInvariant`), key provider down, emergency disable engaged, availability fast-burn | 15 min | 1 h |
| SEV3 | Saturation, slow-burn, latency, replay elevation | business hours | daily |

Paging and escalation follow OWNERS.yaml. Until on-call is staffed (W-003), the accountable owner takes every page.

## Containment

1. **Stop authority.** Contain according to scope:
   - **One workload:** call `table.destroy()`.
   - **One host:** call `emergency_disable()`, or set `INV42_EMERGENCY_DISABLE=1` and restart.
   - **Fleet:** roll out the disable (ROLLOUT.md).
2. **Signing-key compromise:**
   1. Revoke the key and publish the revocation.
   2. Freeze the production channel.
   3. Re-verify every deployed artifact with `tools/release.py verify` against the *new* key list.
3. **Transport PKI compromise:** revoke the certificates and rotate the CA pin.

## Attack

Symptoms: forged, foreign or type-mismatch rejections are rising.

1. Identify the source workload from tracing and log metadata. INV-42 itself never logs owners.
2. Isolate that workload at the platform layer.
3. Rejections are fail-closed, so no authority leaked unless T8 (key compromise) is suspected. If it is, destroy the affected tables.

## Forensics

Preserve evidence before restarting anything. Collect:

- the audit chain file and its anchored head;
- metrics snapshots;
- the release manifest and signature of the running artifact;
- `status()` of the affected tables.

Verify the chain with `audit.verify(path, mac_key=..., expected_head=...)`.

Do **not** capture process memory into ordinary tickets, because it contains table keys.

## Recovery

1. Deploy a verified artifact.
2. Release the emergency disable.
3. Clients re-acquire descriptors (there is no state restore).
4. Confirm that `health()` reports `ready` and the alert has cleared.

## Post-incident

Within 5 business days, write a blameless review:

- add regression tests derived from the incident to the suites;
- add a `REVIEWS.json` entry (`kind: incident`);
- update THREAT_MODEL.md.
