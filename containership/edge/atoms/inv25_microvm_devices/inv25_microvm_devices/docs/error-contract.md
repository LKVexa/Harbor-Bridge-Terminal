# PK_DEVICE_ERROR/1 (work item 11 — C026, C014, C053)

Schema: `schemas/PK_DEVICE_ERROR_1.schema.json`. Serializer: `errors.to_error()`.
Codes are a **permanent compatibility surface**: add, never rename or reuse.

| Code | Category | Retryable | Caller guidance |
|---|---|---|---|
| INV25_INVALID_NAME / _CLASS / _VERSION / _REGISTER / _FIELD | validation | no | fix input |
| INV25_MISSING_RATIONALE / _REVIEWER | validation | no | supply review metadata |
| INV25_FORBIDDEN_LEGACY_EMULATION / _HOST_EXPOSURE | policy | no | never permitted |
| INV25_REPLACE_REQUIRED / _REPLACE_TARGET_ABSENT / _VERSION_NOT_CHANGED | conflict | no | use `replace()` / new version |
| INV25_VERSION_DOWNGRADE | policy | no | reserved for anti-downgrade policy |
| INV25_CONCURRENT_MODIFICATION | conflict | yes | re-read active digest, re-propose |
| INV25_UNAUTHENTICATED / _UNAUTHORIZED / _REPLAY_DETECTED | security | no | obtain valid credential/capability |
| INV25_ARTIFACT_VERIFICATION_FAILED | security | no | investigate supply chain |
| INV25_COMPATIBILITY_MISMATCH | compatibility | no | upgrade peer |
| INV25_LIMIT_EXCEEDED | capacity | no | reduce payload |
| INV25_RATE_LIMITED | capacity | yes | back off (exponential, full jitter, cap 30 s) |
| INV25_DEPENDENCY_UNAVAILABLE / _AUDIT_UNAVAILABLE | dependency | yes | back off; mutations halted meanwhile |
| INV25_DEVICE_DISABLED | policy | no | incident in progress |
| INV25_INTERNAL | internal | no | safe generic mapping for unknown failures |

Details are redacted: keys containing token/secret/key/password/credential/path/trace are dropped,
values outside a safe character class become `[redacted]`. Stack traces are never serialized.
Retries: INV-25 itself never retries internally; retryable codes tell the *caller* retrying is safe
because every mutation is idempotent (candidate IDs, CAS on expected digest, single-use nonces).
