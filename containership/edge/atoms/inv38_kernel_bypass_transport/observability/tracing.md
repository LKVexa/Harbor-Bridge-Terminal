# Trace propagation (INV-38-C074)

`tracing.py` parses/validates incoming trace context, sanitizes privileged
baggage from untrusted callers, and defines span boundaries (register, post,
queue_wait, provider_submit, completion, fallback, retry, config_txn). Sensitive
tenant/payload/address/key fields are redacted; sampling retains errors at a
higher rate. Cross-boundary continuity tests live under
`observability/trace-propagation-tests/` and `tests/test_tracing.py`. **Status:**
`IN_PROGRESS` — full cross-boundary continuity needs adjacent live components.
