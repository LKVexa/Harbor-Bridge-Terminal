# ADR-0002 — Durable state: single-writer WAL + snapshot with fenced lease; replication external

- **Status:** Proposed — awaiting owner approval; multi-host replication remains open (waiver W-004)
- **Date:** 2026-09-23

## Decision
`store.DurableStore` persists every committed version *before* the mutation is acknowledged (write-ahead hook in
`IntentGraph._commit`; a failed write rolls the mutation back). Records are SHA-256 hash-chained and HMAC-sealed
with a versioned key from `KeyProvider`. Snapshots are written atomically (temp + fsync + rename) and compact the
WAL. Exactly one writer is permitted, enforced by `FileLease` with monotonically increasing fencing tokens that are
stamped on every WAL record; a stale holder is refused (`PLN01-E0019`).

## Why not build consensus here
Raft/Paxos correctness is a specialised dependency. For multi-host HA the store interface (`open_graph`,
`_on_commit`, `snapshot`, `append_audit`) is to be backed by an external linearizable store (etcd/FoundationDB class)
whose lease replaces `FileLease`. Until then HA is active/passive with shared storage and fenced failover.

## Consequences
Crash consistency: at most the in-flight, unacknowledged mutation is lost; a torn trailing record is truncated;
any other corruption is fail-stop (`PLN01-E0020`), never silently repaired.
