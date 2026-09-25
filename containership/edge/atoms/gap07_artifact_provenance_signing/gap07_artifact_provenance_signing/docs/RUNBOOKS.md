# GAP-07 operational runbooks (#40)

Every procedure produces audit events. Record the change ticket in the `reason` field.

## R1 Signer onboarding
1. Key ceremony (KEY_CEREMONY.md) → SPKI pin.
2. Issue a `PK_CERT/1` leaf under the intermediate: `usages` = exactly the `sign:<kind>` / `attest:<predicate>` set needed.
3. Add `SignerAuthz` (roles, kinds, predicate types, algorithms).
4. Build the next generation → `sign_config("trust-snapshot" | "trust-distribution")` with the config authority → `FileTrustRepository.stage()` → review the diff → `commit()`.
5. Distribute a delta (`make_delta`) and watch `PropagationTracker.report()` until every site acks.

## R2 Signer offboarding
A delta with `remove_signer` + `revoke_kid`. Artifacts signed earlier stop admitting on the next evaluation. Plan re-signing first when needed.

## R3 Key rotation
Add the new leaf/kid (R1) → let both run through an overlap window → move signers to the new kid → `revoke_kid` the old kid after the retention window. Never re-point an alias. Pinned versions mean KMS alias changes have no effect until a trust generation says so.

## R4 Key compromise (Sev-1)
1. `compromise.respond_to_compromise(...)` → urgent revocation delta + quarantine of the blast radius + evidence package.
2. Publish the delta at once (urgent SLO: 300 s). Watch `gap07_propagation_slo_breach`.
3. Preserve evidence: export audit (`AuditExporter.export`), snapshot the decision log, and record `evidence_digest` in the incident.
4. Run the campaign: rebuild from verified source, then re-sign with the new key. Release quarantine per digest with two approvers.

## R5 Trust-store rollback (bad generation shipped)
Never lower the generation. Issue generation N+1 whose contents equal the last good state. Only disaster recovery may restore below the floor: `restore(backup, recovery_approval={2 approvers, compromise_ruled_out: true})`.

## R6 Transparency-log outage
Admission of kinds whose rule requires transparency returns `TLOG_REQUIRED`. It does not degrade. Options: wait; or issue a signed `PK_WAIVER/1` covering `transparency` for specific digests (≤ 30 d, 2 approvers, compensating control such as manual review). Offline sites keep verifying with cached checkpoints up to `max_checkpoint_age_s`.

## R7 Disconnected site recovery
1. Check `SiteTrustAgent.readiness()` and `TrustedClock.ready()`.
2. On reconnect, `reconcile_plan()` → fetch deltas or a snapshot. Stale objects are refused by construction.
3. Lost secure time (corrupt state or RTC reset): the clock reports `TIME_UNTRUSTED`. An operator gets a fresh signed time attestation through the out-of-band channel. Never edit the floor file by hand.

## R8 Emergency disable / break-glass
Needs a signed `PK_BREAK_GLASS/1` (config authority, 2 approvers, ≤ 24 h, one digest, single-use nonce). Every use emits `admission.break_glass` with `post_event_review: required`. The review must happen within 5 business days.

## R9 Bootstrap of a new or rebuilt site
Install the anchor set, config-authority SPKIs, time-authority SPKI and release-authority SPKI out of band (signed media or console, two-person verification of SPKI fingerprints). Then accept only signed snapshots over the network.

## R10 Audit export health
If `gap07_audit_export_healthy == 0` or the spool exceeds 80 %, investigate the collector. `AUDIT_SPOOL_FULL` blocks security mutations. Verify stored exports daily with `verify_export(path, log_keys=...)`.

## Retention
Audit exports: 7 years (or estate policy) on WORM/object-lock with legal-hold support. Decision logs: 2 years. Quarantine journal: life of the artifact + 1 year. The chain metadata (heads, anchors) is kept forever.
