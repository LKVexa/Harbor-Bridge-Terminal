# Error codes (G13-MC-016)

Append-only; never renamed or reused. Wire form `PK_POLICY_ERROR/1`. HTTP mapping in `rpc.http_status`.

| Code | Class | Retryable | Meaning |
|---|---|---|---|
| `G13-E000` | `PolicyError` | no | Base class for every GAP-13 refusal. |
| `G13-E100` | `BundleRejected` | no | A policy bundle failed validation/verification and was not loaded. |
| `G13-E101` | `ScopeEscalation` | no | A tenant allow rule would widen estate-level authority. |
| `G13-E110` | `BundleParseError` | no | Bundle bytes are not syntactically valid. |
| `G13-E111` | `BundleTooLarge` | no | Bundle exceeds a configured size/count/depth limit. |
| `G13-E112` | `SchemaMismatch` | no | Unsupported or unknown schema version. |
| `G13-E113` | `BundleSemanticError` | no | Bundle parsed but violates semantic rules. |
| `G13-E120` | `VerificationFailed` | no | Cryptographic verification did not yield VERIFIED. |
| `G13-E130` | `ReplayRejected` | no | Bundle generation is at/below the anti-rollback floor, or collides. |
| `G13-E131` | `AntiReplayStateUnavailable` | yes | Durable anti-replay state is corrupt or unreadable; activation refused. |
| `G13-E140` | `BundleQuarantined` | no | Bundle identity/digest/generation is quarantined. |
| `G13-E141` | `UpdateFrozen` | yes | Bundle updates are frozen by operator control. |
| `G13-E200` | `RequestRejected` | no | Evaluation request is malformed or not admissible. |
| `G13-E201` | `AttributeRejected` | no | Attribute unknown, mistyped, or in a protected namespace. |
| `G13-E202` | `RequestTooLarge` | no | Request exceeds attribute count/size limits. |
| `G13-E210` | `ContextUnavailable` | yes | Trusted attribute provider unavailable; fail closed. |
| `G13-E300` | `StalePolicyRefused` | yes | Active bundle is past hard expiry and mode is FAIL_CLOSED. |
| `G13-E301` | `EvaluationDisabled` | yes | Evaluation disabled by emergency control. |
| `G13-E302` | `NoActivePolicy` | yes | No verified bundle is active. |
| `G13-E310` | `Overloaded` | yes | Admission control shed the request. |
| `G13-E311` | `DeadlineExceeded` | yes | Request deadline elapsed before evaluation. |
| `G13-E400` | `Unauthorized` | no | Principal lacks the capability or scope for this operation. |
| `G13-E401` | `Unauthenticated` | no | Credential missing, expired, replayed, revoked or wrong audience. |
| `G13-E500` | `DependencyUnavailable` | yes | An upstream dependency (verifier, distribution, sink) is unavailable. |
| `G13-E501` | `AuditSinkUnavailable` | yes | Audit sink unavailable and buffer exhausted; privileged action refused. |
| `G13-E510` | `CacheCorrupt` | no | Persistent cache failed integrity check. |
| `G13-E600` | `ConfigRejected` | no | Configuration invalid or unsafe. |
