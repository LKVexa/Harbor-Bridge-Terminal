# Backup, restore, migration

- **What:** `state_dir/*.state.json` (must-persist controller state per scope), `config_dir/active.json` + `journal.jsonl`, the durable audit file. Reconstructible (not backed up): explain store, metrics, in-memory audit window.
- **Backup:** crash-consistent file copy (every file is written by atomic rename) every 5 min + on release; RPO 5 min for backups (the live RPO is 0 via persist-before-publish); RTO 15 min.
- **Restore:** stop the instance (or let its lease lapse), copy files back, start; a file that fails its HMAC check is refused (`E_STATE_CORRUPT`) — restore an older copy rather than deleting it. The restored epoch is lower than the live coordination epoch, so the first decision re-acquires the lease with a new epoch; downstream fencing prevents any stale effect.
- **Migration:** the plane reads `PLN05_STATE/1` and `/2` and writes `/2`; future versions are refused. Config reads `PLN05_CONFIG/1`.
- **Reconstruction (no backup):** delete the scope's state file *deliberately* (documented action), re-declare the envelope via PLN-01; the controller restarts at the floor and scales up on demand within one sample per doubling.
- **Rehearsal:** `tests/fault/test_faults.py::test_FS01/FS19`, `tests/test_plane.py::PersistenceAndFailoverTest`; staging drill in REV-GAMEDAY.
