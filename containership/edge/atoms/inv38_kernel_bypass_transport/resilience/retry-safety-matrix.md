# Retry safety (INV-38-C053)

Operations are classified safe-to-retry / retry-with-idempotency-key /
retry-after-reconciliation / never-retry. Data-plane posts are not blindly
retried. Backoff is exponential with bounded jitter; attempts and elapsed time
are capped (`retry.py`, `resilience/retry-policy.yaml`). Clock and randomness are
injectable; tests prove bounded attempts, jitter range, no retry storm and no
duplicate completion. **Status:** `DONE`.
