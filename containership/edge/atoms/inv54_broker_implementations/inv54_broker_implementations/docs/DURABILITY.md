# Durability, recovery, retention, backup  (components 47, 48, 57, 61)

- **Log format:** `storage.DurableLog` — per-partition append-only files, framed `MAGIC|LEN|CRC32|PAYLOAD`, atomic metadata via rename. fsync policy `always|batch|never` (production forbids `never`).
- **Crash recovery (57):** on open, each partition is scanned; a torn tail is truncated and counted (`recovered_truncations`); a corrupt record *followed by valid data* is refused with `INV54-E0503` (never silently skipped). Offsets continue from the last good record.
- **Retention/compaction (48):** `apply_retention(max_records, max_age_s)` advances the persisted low watermark; `compact()` keeps the latest record per key, preserving offsets (gaps allowed). Reads below the watermark → `INV54-E0401`.
- **Backup/restore (61):** `backup()` → tar.gz of partition files + metadata after flush; `restore()` refuses non-empty targets and archives containing paths/links. Migration between format versions: none needed yet (format 1).
- **Not covered:** multi-host durable replication over a network (the HA model in `ha.py` is in-process), point-in-time restore, restore drills on production data → UNVERIFIED.
