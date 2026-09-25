# Backup / restore (M35)

- Backup: `python -m inv65_capability_providers.tools.backup_state backup <state_dir> <archive.json>` (compacts, writes self-verifying archive).
- Verify: `... verify <archive>`.
- Restore: `... restore <archive> <state_dir>`; refuses older-than-live unless `--force-older`; **always** re-applies live tombstones so revoked links cannot return.
- Migration: v1 (4.2.0 in-memory shape) snapshots auto-migrate to v2 on load (`state/migrations.py`).
- Reconstruction without backup: re-apply INV-64 application manifests through INV-60 (links are declarative there).
- Cross-site restore must pass residency: restore only into a region allowed for every tenant in the archive (manual check; automated check is future work).
