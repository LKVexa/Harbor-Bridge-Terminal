# Key custody, rotation and revocation (MC-05)

Implementation: `keys.py`, `handshake.py` (epoch/revocation checks), `audit_log.py` (events).

## Inventory

| Class | Purpose | Storage | Rotation | Destruction | Allowed consumers |
|---|---|---|---|---|---|
| trust_anchor | issue identity credentials | HSM/KMS, offline root preferred | yearly + on compromise | HSM zeroize on retirement | issuer service; verifiers get the public key only |
| identity | sign handshake transcripts | KMS/HSM through workload identity (`secretref://<env>/...`) | 30 days, 7-day grace | provider-side destroy after grace | handshake |
| traffic | PK_CTRL_FRAME/2 AEAD | process memory only, per session | every session; rekey at `session_max_age_s` / `session_max_frames` | reference dropped on close | `transport.Session` |
| quarantine_authority | sign quarantine directives | HSM, break-glass procedure | yearly + on compromise | HSM zeroize | quarantine operators |
| audit_signing | sign audit checkpoints | KMS | 90 days | KMS destroy after retention period | audit log |
| release_signing | sign release artifacts | CI OIDC-bound signer (keyless) or offline HSM | per signer policy | n/a (keyless) | `tools/release.py` |
| test | tests/fixtures | generated per run, `test` namespace | per run | process exit | tests only |

Owners: every class is owned by the security owner role except `release_signing` (release owner). Names are UNASSIGNED (`governance/owners.json`).

## Rules

- Production private keys never appear in source control, configuration, logs, crash dumps, evidence or command lines. Configuration carries only `secretref://<env>/<name>` handles; `config.validate` rejects PEM material and secret-like field names; `tools/secret_scan.py` runs in CI.
- Namespaces `dev`, `test`, `stage`, `prod` are disjoint: a credential's `env` must equal the verifier's `HandshakePolicy.env`, the identity key reference's namespace must equal the configured environment, and `InMemoryKeyProvider` refuses `prod`.
- Loggable identifiers: `KeyMetadata.safe()` (key ID, class, algorithm, epoch, state, namespace) - never key bytes.
- Providers sit behind `KeyProvider`; returned metadata is validated (algorithm, namespace, class, state, epoch >= minimum, expiry) before use. `KeyCache` keeps handles for a bounded TTL and destroys evicted/invalidated handles.
- Python cannot guarantee zeroization: handles drop private-key references on `destroy()`/eviction and refuse pickling; physical memory is not scrubbed (documented limitation, debt D-001).

## Epochs, rotation, revocation

- Credentials carry `key_epoch`. `EpochPolicy` accepts `current`, and `previous` only until `grace_until`. Epochs strictly increase; mixed/ambiguous epochs cannot be accepted because a session uses exactly the two credentials proven in its handshake.
- Scheduled rotation: `rotate(n+1, grace_s)`. Live sessions are unaffected until they reach max age; new handshakes accept both epochs during grace, only `n+1` after.
- Emergency revocation: `revoke(epoch)` or revoke the credential serial at the revocation feed - new sessions are refused immediately; existing sessions for affected subjects are terminated with a `terminate_sessions` quarantine directive.
- Rollback to an older epoch is denied unless `recovery_authorization` (incident/approval ID) is supplied; revoked epochs can never be rolled back to. All of these emit `key.*` audit events.
- Maximum session age (default 3600 s) and frame count are mandatory rekey triggers; credential rotation, trust-anchor rotation and policy changes are re-authentication triggers (existing sessions are drained at their next rekey or terminated by directive if urgent).

## Failure handling

| Condition | Behaviour |
|---|---|
| KMS unavailable / throttled | bounded retries (`retry_call`, full jitter, honours `retry_after_s`), then `KEY_UNAVAILABLE`/`KEY_THROTTLED`; new handshakes fail closed |
| permission denied | `KEY_PERMISSION`, no retry |
| stale replica (old epoch) | `KEY_EPOCH` when below the minimum epoch |
| corrupted response (unexpected algorithm) | `KEY_INTEGRITY`, fail closed |
| clock failure | handshake `HS_DEPENDENCY` (time is validated before any credential check) |

Tests: `tests/test_control_planes.py::KeyCustodyTest`, `tests/test_handshake.py`, `tests/test_endpoint_integration.py::DisasterPartitionTest::test_key_rotation_and_revocation_under_active_traffic`. Production KMS/HSM adapters are **not** shipped (debt D-002).
