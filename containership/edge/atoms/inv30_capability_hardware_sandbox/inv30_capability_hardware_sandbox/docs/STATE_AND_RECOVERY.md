# State, crash consistency, backup/restore decision (INV30-GAP-037, GAP-065 · INV-30-C057, C058, C095)

**Decision: backup/restore of capability state is NOT APPLICABLE by design.**

* Capability handles are authority. Restoring authority from a backup would resurrect capabilities that may have
  been invalidated after the backup — a direct violation of REQ-004. Therefore the handle table is volatile.
* **Restart semantics:** after any crash/restart the table is empty; every old handle returns `NOT_FOUND`; clients
  re-acquire roots through the MintingAuthority (reconstruction, not restore).
* **Replay:** there is no replay of mutating operations; idempotency keys make client retries safe within a process
  lifetime only.
* **What IS persisted and backed up:** the audit ledger (append-only, fsync per event, head exported to an external
  anchor for truncation detection), the ConfigStore history, the rollout state. Back these up with the host's
  standard file backup; restore = copy back and `AuditLedger.verify(expected_head=<anchored head>)`.
* **Migration:** schema major bump → dual-stack one release; config migrations via ConfigStore with provenance.
* **Split-brain (C058):** single-writer fencing `Lease`; a superseded instance refuses mint/derive.
