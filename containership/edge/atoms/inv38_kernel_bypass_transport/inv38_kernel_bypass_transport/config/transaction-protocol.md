# Transactional config updates (INV-38-C037)

Prepare→validate→stage→commit with a transaction ID and monotonic generation
(`config_txn.py`, `config/transaction.schema.json`). The entire candidate is
validated before an atomic generation swap; readers see old-or-new, never a torn
mix. Commit failure restores the prior known-good generation and records an
auditable failure. Concurrent updates use optimistic version preconditions.
Fault-injection tests in `tests/test_config_txn.py`. **Status:** `DONE`.
