# Backup / restore / migration / reconstruction — explicit statelessness decision (C095)

**Decision:** INV-35 holds **no durable state of its own**. Everything is either
(a) immutable release content, (b) operator configuration owned by the config
system of record, or (c) runtime state reconstructible from the guest and the
controller.

| State | Durable? | Backup | Reconstruction |
|---|---|---|---|
| Queue registrations & regions | no | — | controller re-registers from INV-24/INV-25 after restart |
| In-flight reservations | no (journal is process-lifetime) | journal snapshot for crash-restart on the same host | `Runtime.recover(journal)`; guest rings are the source of truth thereafter |
| Idempotency keys | no | in journal | replayed from journal; after full host loss the guest re-posts (idempotency scope is per host) |
| Config | external | config system of record | re-apply; digest must match provenance |
| Audit chain | exported | SIEM (400 d) | chain verified on ingest; new process starts a new chain linked by `runtime.recovered` event |
| Keys | external (KMS) | KMS | — |

Migration of a guest between hosts is owned by INV-24: the destination registers
new queues; the source drains and stops. No INV-35 state is copied.
Approval: **PENDING** (accountable_owner).
