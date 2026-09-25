# ADR-004 — Durability: WAL + atomic snapshots, fsync before acknowledge

* Status: **Proposed** · Traceability: C013, C057, MC-006, MC-018-05

* Every mutation is a deterministic record; it is framed (`CSW1|len|crc32|payload`), written and **fsync-ed before** it is applied or acknowledged (`durability=fsync`, default). `group` durability (bounded loss envelope `group_commit-1` writes) must be opted into; `none` is test-only.
* Snapshots: write tmp → fsync → rename → fsync dir; generations numbered; current and previous generation retained.
* Recovery: newest snapshot + WAL generations ≥ it; incomplete tail frame = unacknowledged torn write → truncated and reported; any complete-but-invalid frame, mid-file damage or bad snapshot checksum ⇒ `CorruptionError` (fail closed, operator restores or explicitly allows tail truncation).
* Any journal error at runtime puts the store in `FAILED` (reads and writes refused) because memory and disk may diverge; the in-flight write's outcome is ambiguous (`CSTATE_FAILED` is idempotency-sensitive).
* Lease deadlines are volatile: after recovery every lease is re-armed with its full TTL (never shortened), so a holder never loses a lease *earlier* than its TTL; fencing tokens are durable and strictly increasing, so a stale holder cannot write protected keys after a new grant.
