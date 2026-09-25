# Incident response (C097)

| Severity | Examples | Page | Ack | Containment first step |
|---|---|---|---|---|
| SEV1-security | successful cross-tenant restore; integrity failures; entropy failures at scale | inv26-security + inv26-oncall | 5 min | emergency disable on affected sites |
| SEV2(-security) | dependency outage; security boundary probing; audit buffering | inv26-oncall | 15 min | none required (fail-closed); rate-limit the probing principal, revoke its key |
| SEV3 | overload, stalls, single-node issues | inv26-oncall (business hours) | 60 min | — |

Paging destinations are **unassigned** (`ops/ownership.json` on_call = null) — this document is therefore not
operable until the owner assigns them (C097 GOVERNANCE_PENDING).

## Playbooks
* <a id="security-boundary-probe"></a>**Security boundary probe:** identify principal from decision records
  (`explain`), revoke its key (`TrustStore.revoke`), preserve the audit chain (`audit verify` + copy anchor).
* <a id="integrity"></a>**Integrity failure:** scrub → affected snapshots QUARANTINED; do **not** release without
  break-glass + security review; determine storage fault vs tampering from the audit trail and storage logs.
* <a id="entropy"></a>**Entropy failures:** guests are destroyed automatically; check the guest agent image and
  vsock path; never disable the reseed requirement (LOCKED).
* <a id="defect"></a>**Defect (SNAP_INTERNAL):** correlation id → decision record + log line; roll back per
  ROLLOUT_POLICY if it started after a release.
* **Recovery:** after containment, `reconcile()`, `scrub()`, `health()`, then re-enable; post-incident review
  recorded in `ops/REVIEWS.json` records.
