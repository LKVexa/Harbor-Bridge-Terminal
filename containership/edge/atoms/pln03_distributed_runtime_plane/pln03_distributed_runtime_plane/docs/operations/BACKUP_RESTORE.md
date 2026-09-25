# Backup, restore, migration, reconstruction (MC-050)

- **What:** durable adapter journals (`*.wal`), audit JSONL, config ledger export (`ConfigStore.ledger()` + revision configs).
- **Backup:** copy journal after `fsync`; journals are append-only, so a copy is always a valid prefix. Hash each copy into the evidence bundle.
- **Restore:** start `DurableAdapter` on the copy; replay reports `replayed`; torn tail is discarded. Verified by `test_mc047_mc050_restart_restore_from_journal_copy`.
- **Migration:** journal records are versioned by `op`; new ops are additive. A schema change requires a migration tool that replays old journal → writes new journal; not needed for 4.3.0.
- **Reconstruction:** if journals are lost, state is reconstructed from the backing store owned by INV-49; PLN-03 holds no system-of-record data beyond its journals.
- **Targets:** RPO 0 (fsync per record), RTO ≤ 5 min (NFR-DUR-02).
