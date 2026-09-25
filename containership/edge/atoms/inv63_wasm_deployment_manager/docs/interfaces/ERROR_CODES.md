# INV-63 structured error codes (INV-63-C026)

Generated from `errors.py`; test `test_error_catalog_complete` fails if this drifts.

| Code | Retryable | Outcome |
|---|---|---|
| `INV63-E-INVALID-REQUEST` | False | TERMINAL |
| `INV63-E-SCHEMA` | False | TERMINAL |
| `INV63-E-UNSUPPORTED-VERSION` | False | TERMINAL |
| `INV63-E-PAYLOAD-TOO-LARGE` | False | TERMINAL |
| `INV63-E-UNAUTHENTICATED` | False | TERMINAL |
| `INV63-E-FORBIDDEN` | False | TERMINAL |
| `INV63-E-REPLAY` | False | TERMINAL |
| `INV63-E-TENANT-ISOLATION` | False | TERMINAL |
| `INV63-E-ARTIFACT-UNTRUSTED` | False | TERMINAL |
| `INV63-E-INSUFFICIENT-CAPACITY` | True | RETRYABLE |
| `INV63-E-QUOTA` | False | TERMINAL |
| `INV63-E-OVERLOADED` | True | RETRYABLE |
| `INV63-E-CIRCUIT-OPEN` | True | RETRYABLE |
| `INV63-E-DEADLINE` | True | RETRYABLE |
| `INV63-E-CANCELLED` | False | TERMINAL |
| `INV63-E-DEPENDENCY-UNAVAILABLE` | True | RETRYABLE |
| `INV63-E-CONTROL-PLANE-OFFLINE` | True | RETRYABLE |
| `INV63-E-STALE-EPOCH` | False | TERMINAL |
| `INV63-E-CONFLICT` | True | RETRYABLE |
| `INV63-E-ILLEGAL-TRANSITION` | False | TERMINAL |
| `INV63-E-QUARANTINED` | False | TERMINAL |
| `INV63-E-FROZEN` | False | TERMINAL |
| `INV63-E-CONFIG-INVALID` | False | TERMINAL |
| `INV63-E-SECRET-IN-CONFIG` | False | TERMINAL |
| `INV63-E-STATE-CORRUPT` | False | TERMINAL |
| `INV63-E-ROLLOUT-FAILED` | False | TERMINAL |
| `INV63-E-PRECONDITION` | False | TERMINAL |
| `INV63-E-POLICY` | False | TERMINAL |
| `INV63-E-INTERNAL` | False | TERMINAL |

Every error is emitted as `PK_DEPLOY_ERROR/1` with `details` (machine-readable, redacted) and optional `retry_after_s`.
