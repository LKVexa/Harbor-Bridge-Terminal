# Runbooks — day 0 / 1 / 2, rollout, rollback, emergency controls, backup (MC-25, MC-37, C092, C095, C096)

## Day 0 — bootstrap from empty (C040)
```bash
python -m venv .venv && . .venv/bin/activate
pip install --require-hashes -r requirements.lock        # stdlib-only runtime: lock is empty by design
pip install .                                             # or: python -m build && pip install dist/*.whl
python -m pln02_application_plane.tools.gate --tier local # tests (normal + -O), manifest, traceability, evidence
```
Provision keys (catalogue, token, audit, artifact) in the KMS; write `PK_PLANE_CONFIG/1` with provenance;
`ConfigManager(root).activate(cfg)`; start one controller per store root (it acquires the fencing epoch).

## Day 1 — staged rollout (canary)
| Stage | Scope | Duration | Advance only if | Automatic rollback trigger |
|---|---|---|---|---|
| 0 | shadow: resolve, do not publish (`--dry-run` caller) | 1 h | 0 `INTERNAL`; identical revisions vs. previous version | any `INTERNAL` or identity drift |
| 1 | 1 tenant, 1 site | 24 h | SLO alerts silent; rejection mix unchanged ±10 % | `ResolutionLatencySLO`, `IntegrityFailure`, `InternalErrors` |
| 2 | 10 % tenants | 24 h | same | same |
| 3 | all | — | gate verdict GO on the exact artifact digest | same |

## Rollback
- Revision: `store.rollback(tenant, environment, application, epoch)` → head points to previous non-quarantined revision.
- Configuration: `ConfigManager.rollback()` → last-known-good (digest verified).
- Software: redeploy previous wheel (digest from previous gate evidence); store format is unchanged in 4.x.

## Emergency controls (all audited, require `plane-admin`)
`service.admin(token, "freeze", "<tenant>|<tenant>/<env>|*")` · `"disable"` · `"quarantine", "<revision>"` ·
`"release"` / `"unfreeze"` / `"enable"` to reverse. Key compromise: `KeyRing.revoke(kid)` then rotate.

## Backup / restore / reconstruction
- Backup: `store.backup(dest)` (verifies on completion); copy audit ledger + anchor its head (`AuditLedger.head`).
- Restore: `RevisionStore.restore(backup, empty_root)` bumps the fencing epoch so every pre-backup controller is fenced.
- Reconstruction: revisions are content-addressed; any revision can be re-derived from its application document +
  catalogue snapshot (digest in provenance) + config digest, and must reproduce the same address.

## Drills
Drill scripts are the tests `MC24MC25Store.*` and `MC06MC33Disconnected.*`. **No production drill has been
executed from this archive**; MC-37 stays PARTIAL until a dated drill report is attached.
