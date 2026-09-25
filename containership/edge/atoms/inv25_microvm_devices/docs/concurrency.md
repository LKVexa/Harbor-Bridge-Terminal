# Concurrency model (work item 25 — C086, C058)

`DeviceCatalogue` (model) is **not thread-safe** and is intended for single-owner, in-process use.
`CatalogueStore` is the supported shared object:
- One re-entrant lock serializes every mutation and history read.
- The active catalogue is an immutable `Snapshot` swapped by single reference assignment, so readers
  never lock and always see a complete old or new state.
- Activation is compare-and-swap on `expected_digest`; concurrent candidates built on the same base
  produce exactly one winner (`ConcurrencyTest`).
- Audit events are emitted before the commit point; a failed commit is followed by
  `config.activation_failed`, so the chain order is: attempt → (activated | activation_failed).
- Rollback and activation share the lock and the CAS check — they cannot interleave.
- Retries after an ambiguous timeout: re-activating the same candidate returns the original record.
Cross-process or multi-node sharing requires an external store providing the same CAS contract and
is not certified by this package.
