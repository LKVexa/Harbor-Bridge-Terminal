# ADR-007: Trust persistence
Status: accepted
Decision: file-based repository of immutable signed generation documents + atomic pointer + monotonic floor. No SQLite (edge simplicity, byte-preserving export). Estates that need HA replicate the directory via the distribution protocol, not via shared storage.
