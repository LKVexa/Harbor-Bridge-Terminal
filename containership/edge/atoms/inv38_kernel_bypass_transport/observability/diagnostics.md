# Safe high-cardinality diagnostics (INV-38-C075)

A privileged diagnostics level, separate from tenant status, keyed on opaque IDs
(operation/queue/region-fingerprint/provider/config-generation) rather than
secrets. Query range/rows/bytes/time/concurrency are bounded to prevent
diagnostic DoS; every privileged query is rate-limited and audited. Redaction
rules: `observability/redaction-policy.yaml`. Adversarial tests in
`tests/test_logging.py`. **Status:** `DONE`.
