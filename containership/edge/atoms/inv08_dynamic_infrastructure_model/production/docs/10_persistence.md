# INV-08 source-of-truth persistence architecture (PROPOSED)

## Lease data model (authoritative)
`lease(tenant, node_id) -> {holder, expires: number, busy: bool, revision: int, fence: int}`;
key = (tenant, node_id).  A node without a live lease is not in the pool (contract.py).
Reference double: `production/concurrency.py::LeaseTable`.

## Technology selection - BLOCKED
Candidates: etcd (Raft, linearizable txn, leases native), PostgreSQL (serializable
isolation, synchronous replica), FoundationDB (strict serializable).  No decision
owner exists (ownership.json UNASSIGNED); ADR-0001 keeps this open.

## Required guarantees (any candidate must meet)
- Linearizable writes to a lease key; reads used for reclaim decisions must be linearizable.
- Durability: acknowledged write survives loss of one failure domain (>= 3 replicas, quorum commit).
- Fencing: every mutation carries the lease `fence` and leader `epoch`; stale values are rejected (implemented in the double, tested in test_govops ConcurrencyTest).
- Conflicting writers: compare-and-swap on `revision`; losers get RETRYABLE_FAILURE (`INV08.LEASE.CAS_CONFLICT`), stale fence/epoch get TERMINAL_FAILURE.

## Backup, restore, compaction, retention
- Backup/restore/migrate/reconstruct: `production/backup.py` (format PK_DYN_BACKUP/2, HMAC integrity; encryption BLOCKED on KMS).
- Compaction: expired idle leases are deleted by reclaim; revision history is not retained beyond the audit log.
- Retention: audit records follow `audit.may_delete` (legal hold honoured).
