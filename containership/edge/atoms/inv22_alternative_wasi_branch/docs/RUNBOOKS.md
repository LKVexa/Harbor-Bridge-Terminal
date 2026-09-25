# INV-22 operational runbooks (v4.3.0)

All commands assume the package is installed (`pip install inv22-alternative-wasi-branch`) or run as
`python -m inv22_alternative_wasi_branch.cli`. Every command prints JSON and exits non-zero on failure.
These procedures are written but **not yet drilled** (MC-59).

## RB-00 Day-0 bootstrap (MC-47)
1. Create a clean virtualenv on a supported Python (3.10–3.13).
2. `pip install --require-hashes -r requirements.lock` then `pip install --no-deps <wheel>`.
3. Supply `pk_core` (MC-01) and the pinned baselines in `baselines/manifest.json` (MC-05).
4. `inv22 preflight --strict` — must exit 0. It will refuse while anything is unpinned.
5. Write the site config (secrets as `secret://` references) and activate it through `Ops.activate_config`.
6. `inv22 evidence --out evidence/` and confirm `gate.json` → `GO`.

## RB-01 Unclassified interface blocks a release
Symptom: `INV22.CLASSIFY.UNCLASSIFIED` or completeness `unclassified > 0`.
1. `inv22 completeness data/matrix.json <workload>.wit` to list the IDs.
2. `inv22 wit-diff standards.wit fork.wit` to see the structural diff.
3. Add a reviewed entry to `data/overrides.json` (reviewer + approval date + rationale; shimmable needs `shim_id` and `proof_ref`).
4. `python -m inv22_alternative_wasi_branch.reference` then `--check`; open a PR (two reviewers for any move to shimmable/identical).

## RB-02 Uncertified run reached execution (SLO `no_silent_divergence` breached)
1. Contain: `Ops.freeze_site(token, site, True, reason="INC-…")` — new admissions stop immediately.
2. `inv22 audit-verify <store>`; find `admission.*` events for the workload.
3. Revoke the offending certificate if it was wrong: `Ops.revoke_cert`.
4. Unfreeze only after admission for the site succeeds for every expected workload.

## RB-03 Site branch change
1. Build the impact plan: `governance.plan_branch_change(...)` — must be `ok: true`.
2. Read current `epoch` from `store.site_state(site)`; call `Ops.set_site_branch(..., fence=epoch, plan=plan)`.
3. A `INV22.STATE.STALE_FENCE` means another controller won; re-read state, never force.

## RB-04 Signing-key compromise
1. Mark the key `revoked: true` in the trust store and distribute it — every certificate signed by that key stops verifying.
2. Provision a successor key (`active_from` = now) and re-issue certificates for affected components.
3. Record the incident with `store.record_event(action="key.compromise", …)`.

## RB-05 Drift gate blocks a release
`drift.block` or `drift.review_required` denied. Record the release with `store.record_drift`, review the per-interface diff; a review-required deny may be waived only by a scoped, independently approved, ≤90-day waiver (never for semantic/security/integrity tiers).

## RB-06 Configuration rollback (MC-48)
`Ops.rollback_config(token, site=…, reason=…)` re-activates the previous known-good revision after re-validating it. The audit log records both revisions.

## RB-07 Backup and restore (MC-60)
- Backup: `store.backup(path)` — verifies integrity and the audit chain of the copy before returning.
- Restore: stop writers, copy the verified backup into place, run `inv22 audit-verify`, then `inv22 preflight --strict`.
- A restore never revives trust: revocations in the backup are preserved; certificates revoked after the backup must be re-revoked from the incident record.
- **Open:** RPO/RTO targets need owner approval.

## RB-08 Store integrity failure
`INV22.INTEGRITY.CORRUPT` on read: stop admissions (RB-02 step 1), restore from the last verified backup (RB-07), re-apply revocations from the audit record.
