# RB-04-backup-restore — PROPOSED, drills NOT executed

`state.backup(journal, dest)` writes a manifest (head, seq, sha256). Restore with `state.restore`; it refuses digest/head mismatch.

Owner: UNASSIGNED. Last drill: never.
