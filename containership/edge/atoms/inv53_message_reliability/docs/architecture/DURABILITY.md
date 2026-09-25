# Durability, crash consistency, ownership and failover (C055, C057, C058)

## Write path
`DurableQueue._append`: check not closed / not fail-stopped → read the epoch file →
write one JSON line `{seq, epoch, op, a, h}` to `journal.jsonl` (unbuffered fd) → `fsync` (config `fsync`,
default on) → apply to memory. A write or fsync error fail-stops the instance: memory is no longer trusted
and the broker reopens the store so **replay decides** whether the record landed (`E_STORAGE` is therefore
"indeterminate, retry idempotently").

## Recovery
Load `snapshot.json` (digest-verified; unknown schema refused) → replay records with `seq > snapshot.seq`,
verifying the hash chain and contiguity. A final record without its newline that fails verification is a torn
write: truncated and reported in `recovery_notes`. Any other failure raises `CorruptStoreError`; the broker
freezes that queue (`E_CORRUPT`) and an operator restores from backup.

## Tail completeness
A hash chain proves order and integrity but not that the *last* records are still there. Two mechanisms:
- **Clean shutdown marker.** `close()` writes `CLEAN = {state: closed, seq, head}` atomically; opening sets it to
  `{state: open}`. After a clean close the journal must end exactly at the recorded head, and no torn tail is
  legitimate — any shortfall raises `CorruptStoreError`.
- **External anchor.** `head()` returns `{seq, head}`; pass it back as `DurableQueue(..., anchored_head=…)` to
  prove that a store reopened after a *crash* still contains that head. Without an anchor, recovery after a crash
  records "tail completeness is proven only by an external anchor" in `recovery_notes`.

A crash between compaction's snapshot write and journal reset leaves already-folded records in the journal;
recovery skips records with `seq ≤ snapshot.seq` and resumes the chain from the snapshot head. Any compaction
I/O failure fail-stops the writer.

## Ownership and split brain
- Same host: an exclusive non-blocking OS lock on `LOCK`; a second writer gets `OwnershipError`. The OS
  releases the lock when a crashed owner dies, so takeover needs no manual cleanup.
- Shared storage: each opener publishes `EPOCH = previous + 1` with `os.replace`. Every append re-checks
  the epoch; an older writer receives `EpochFencedError` and stops. This is a fencing token, not a
  consensus protocol: **choosing** which node should own a store across hosts needs an external lease
  service (etcd/ZooKeeper/INV-54 broker) — BLOCKED here (DEBT-01).

## Residency and consistency
A store lives in exactly one directory on one site; there is no cross-site replication in INV-53, so data
residency equals the store path. Within a store, operations are linearizable (one lock, one journal order).

## Compaction, backup, restore, migration
Compaction snapshots the state atomically and resets the journal. Backup = compaction + copy + sha256
manifest (including the state digest). Restore verifies the manifest, refuses a non-empty target, replays,
and compares the state digest. Migration: a new `inv53.store/N` must register a migration in
`DurableQueue._migrate`; unknown versions are refused rather than guessed.
