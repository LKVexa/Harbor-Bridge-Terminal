# Structured logging (INV-38-C073) & diagnostics (C075)

`logging_schema.py` emits bounded, enumerated structured records with stable
node/tenant/workload/component/operation identifiers and redaction of secrets,
MR keys, payloads and (policy-permitting) raw addresses. Untrusted strings are
control-char escaped so they are data, not structure. Diagnostics are bounded and
opaque-keyed (`observability/redaction-policy.yaml`). Schema:
`observability/logging.schema.json`. Redaction/injection tests:
`tests/test_logging.py`. **Status:** `DONE`.
