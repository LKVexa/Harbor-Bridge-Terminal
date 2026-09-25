# Error catalog (M13)

Source of truth: `errors/mapping.py::CATALOG`. Envelope: `schemas/pk_provider_error/v1.json`.

| Code | Retryable | HTTP | Meaning |
|---|---|---|---|
| `PK_PROVIDER_ERROR` | no | 500 | unclassified provider failure |
| `PK_PROVIDER_NO_LINK` | no | 404 | no established, non-revoked named link |
| `PK_PROVIDER_INVALID_LINK` | no | 400 | link/operation failed validation |
| `PK_PROVIDER_UNAVAILABLE` | yes | 503 | backing capability unhealthy |
| `PK_PROVIDER_UNAUTHENTICATED` | no | 401 | caller identity not proven |
| `PK_PROVIDER_FORBIDDEN` | no | 403 | authorization decision absent, denied, stale or mismatched |
| `PK_PROVIDER_DEADLINE_EXCEEDED` | yes | 504 | call deadline elapsed |
| `PK_PROVIDER_CANCELLED` | no | 499 | caller cancelled |
| `PK_PROVIDER_OVERLOADED` | yes | 429 | admission control / quota / rate limit shed the call |
| `PK_PROVIDER_CIRCUIT_OPEN` | yes | 503 | circuit breaker open for the backend |
| `PK_PROVIDER_IDEMPOTENCY_CONFLICT` | no | 409 | idempotency key reused with different request |
| `PK_PROVIDER_FENCED` | no | 409 | stale lease epoch / not the owner |
| `PK_PROVIDER_RESIDENCY` | no | 403 | residency/locality policy forbids placement |
| `PK_PROVIDER_SECRET_UNAVAILABLE` | yes | 503 | secret reference could not be resolved |
| `PK_PROVIDER_DISABLED` | no | 503 | provider or link administratively disabled/draining |
| `PK_PROVIDER_INCOMPATIBLE` | no | 426 | no mutually supported contract version |
| `PK_PROVIDER_UNTRUSTED_ARTIFACT` | no | 403 | implementation digest not allowlisted |
| `PK_PROVIDER_STATE_CORRUPT` | no | 500 | durable state failed integrity check |
| `PK_PROVIDER_KEY_UNAVAILABLE` | yes | 503 | encryption key unavailable |

Success semantics (C014): 200 = success; partial success is not a provider outcome (backends return a whole result or a fault); degraded operation = health `degraded` + only degraded ops served; retryable vs terminal = the Retryable column. Unknown codes from newer peers decode as `PK_PROVIDER_ERROR` (non-retryable).
