# Security Notes — INV-70 v4.3.0

## Trust boundary

- **Guest:** reference bytecode, or a Wasm module on the ADR-0001 profile. Untrusted.
- **Caller:** untrusted until its signed token verifies (C023).
- **Host capabilities:** trusted code supplied by the embedder. They run in the parent process, and each call is bounded by a timeout.
- **Trust store, time source, audit sink:** critical dependencies. If any one of them is lost, the sandbox goes to HALT and rejects everything (C048, C056).

## Controls added in 4.3.0

| Control | Requirement | Code |
|---|---|---|
| Signed, expiring, audience-bound caller tokens with replay cache and immediate revocation | C023 | `security.Authenticator` |
| Attestation verification for node, peer, artifact-provider and control-plane roles | C044 | `security.verify_attestation` |
| Artifact signature, digest, deny list, approved version, builder provenance and SBOM checked before compilation | C045 | `security.verify_artifact` |
| Fail-closed on trust or time loss | C048 | `TrustStore.available`, `Clock.healthy` |
| Hash-chained, HMAC-sealed audit log that detects edits, reordering, deletion and truncation; a sink failure stops unaudited results | C049 | `security.AuditLog` |
| Process isolation with wall-clock kill; host-call timeout and budget | C025, C031 | `executor.ProcessExecutor` |
| Capabilities limited to what the token grants (security precedence) | C019 | `service.Sandbox._handle` |
| Telemetry redaction and tenant pseudonymisation | C079 | `telemetry.redact` |
| Fuzzing of every untrusted parser and boundary | C085 | `tests/test_fuzz.py` |

## Residual limitations (tracked in EXCEPTIONS.yaml)

1. **The Wasm engine is not installed** (C031, EXC-002). The interim production profile is the reference VM in a single-use process. That gives OS-process isolation, but no seccomp or namespace sandbox is applied to the child. Apply one when deploying (for example, run under a restricted user or container).
2. **HMAC tokens** (EXC-003). Anyone holding the verification key can mint tokens. Store keys in a KMS and move to asymmetric signatures.
3. **A hung host callback** is abandoned after its timeout. Its thread may linger, and the pool is capped at 4 threads, so capability owners must still honour their own deadlines.
4. **Side channels** (timing, cache) are out of scope.
