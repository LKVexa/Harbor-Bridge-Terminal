# INV-45 error catalog

Generated from `production/errors.py` registry version 1.0.0; do not edit by hand.

| Code | Wire | Category | Severity | Retryable | HTTP | Operator guidance |
|---|---|---|---|---|---|---|
| `SFI_SCHEMA_INVALID` | 1001 | input | medium | no | 400 | Request/config does not match its versioned schema; fix the producer. |
| `SFI_MALFORMED_ARTIFACT` | 1002 | input | high | no | 422 | Binary is not a well-formed Wasm module; reject the artifact, do not retry. |
| `SFI_INVALID_MODULE` | 1003 | input | high | no | 422 | Module fails Wasm type validation; reject the artifact. |
| `SFI_UNSUPPORTED_FEATURE` | 1004 | compatibility | medium | no | 422 | Module uses a Wasm feature outside the pinned profile (ADR-0001). |
| `SFI_UNSUPPORTED_VERSION` | 1005 | compatibility | medium | no | 409 | Schema/profile/binary version not in the supported set; upgrade the peer or use a supported version. |
| `SFI_UNMASKED_ACCESS` | 2001 | security | critical | no | 422 | A memory access is not confined by the canonical mask sequence; the artifact must be (re)written by the trusted rewriter. |
| `SFI_BRANCH_OUTSIDE_TARGETS` | 2002 | security | critical | no | 403 | Indirect control transfer outside the permitted target set. |
| `SFI_NOT_VERIFIED` | 2003 | security | critical | no | 403 | Execution attempted without a current verification seal. |
| `SFI_SEAL_MISMATCH` | 2004 | security | critical | no | 403 | Sealed descriptor does not match the artifact, profile, config or tenant presented at load time. |
| `SFI_DIGEST_MISMATCH` | 2005 | security | critical | no | 403 | Artifact bytes changed between verification and load (possible TOCTOU). |
| `SFI_SIGNATURE_INVALID` | 2006 | security | critical | no | 403 | Signature missing, malformed, from an untrusted/revoked key, or expired. |
| `SFI_ROLLBACK_REJECTED` | 2007 | security | high | no | 409 | Artifact/policy version is older than the anti-rollback floor. |
| `SFI_POLICY_REJECTED` | 2008 | policy | high | no | 403 | Artifact is valid but disallowed by policy (imports, memory layout, tables, grow). |
| `SFI_QUARANTINED` | 2009 | policy | high | no | 423 | Target (artifact, tenant or global) is quarantined/frozen/disabled by an operator. |
| `SFI_REPLAY_DETECTED` | 2010 | security | high | no | 403 | Authorization token or descriptor nonce was already used. |
| `SFI_UNAUTHENTICATED` | 3001 | auth | high | no | 401 | Caller identity missing, forged or expired. |
| `SFI_UNAUTHORIZED` | 3002 | auth | high | no | 403 | Authenticated caller lacks the explicit capability for this operation/tenant/digest. |
| `SFI_DUAL_AUTH_REQUIRED` | 3003 | auth | high | no | 403 | High-impact action needs a second, distinct authorized principal. |
| `SFI_RESOURCE_LIMIT` | 4001 | resource | medium | no | 413 | Input exceeds a configured size/count/work limit; deterministic, do not retry unchanged. |
| `SFI_OVERLOADED` | 4002 | resource | medium | yes | 503 | Admission control shed the request; retry with backoff+jitter. |
| `SFI_DEADLINE_EXCEEDED` | 4003 | resource | medium | yes | 504 | Operation exceeded its deadline and was cancelled with no partial trust state. |
| `SFI_CANCELLED` | 4004 | resource | low | yes | 499 | Operation cancelled by caller; no partial trust state was created. |
| `SFI_DEPENDENCY_UNAVAILABLE` | 5001 | dependency | high | yes | 503 | A required dependency (engine, key service, config store) is unavailable; fail closed, retry later. |
| `SFI_TRUST_STALE` | 5002 | dependency | high | yes | 503 | Trust material (keys/revocations/config) exceeded its freshness window; refresh before trusting. |
| `SFI_CONFIG_INVALID` | 6001 | input | high | no | 400 | Configuration failed validation; the previous active generation stays in force. |
| `SFI_CONFIG_CONFLICT` | 6002 | input | medium | yes | 409 | Configuration generation changed concurrently (compare-and-swap failed); re-read and retry. |
| `SFI_ILLEGAL_TRANSITION` | 6003 | internal | high | no | 409 | Lifecycle transition not allowed by the state machine. |
| `SFI_AUDIT_TAMPERED` | 7001 | security | critical | no | 500 | Audit chain verification failed; preserve evidence, page security owner. |
| `SFI_INTERNAL_INVARIANT` | 9001 | internal | critical | no | 500 | Internal invariant failed; treated as terminal and fail-closed. File a defect. |

Unknown future codes: consumers use `category`/`retryable`; an unknown category is terminal.
Security and policy rejections are never retryable (deterministic verifier rejection is never retried).
