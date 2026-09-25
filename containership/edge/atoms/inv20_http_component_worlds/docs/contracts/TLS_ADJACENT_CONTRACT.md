# TLS adjacent-layer contract (component 7)

INV-20 does **not** terminate or originate TLS. This contract states what the owning transport layer
must prove so C047/C048 can close on cross-component evidence.

| Item | Requirement | Status |
|---|---|---|
| Owning layer | Named transport component (e.g. host HTTP client in the component runtime) | **UNASSIGNED** |
| Plaintext boundary | Plaintext exists only inside the host process between INV-20 and the transport; never on the wire, never in logs/evidence | Specified |
| Protocol policy | TLS 1.3 preferred, TLS 1.2 minimum with AEAD suites; no renegotiation | Specified, not verified |
| Peer validation | Full chain to the configured trust store; hostname = `Destination.sni`; `check_identity_coherence()` called with the presented SAN list | Hook implemented (`egress.py`) |
| SNI/Host coherence | requested authority == Host == SNI == certificate identity | Hook + tests |
| Trust store | Owned and updated by the transport layer; version recorded in evidence | UNASSIGNED |
| mTLS | Client cert from workload identity (ADR-0004) when the upstream requires it | Specified |
| Expired / not-yet-valid / revoked | Hard fail, `E_UPSTREAM_CONNECT` (non-retryable variant to be added when the layer exists) | Specified |
| KMS / time outage | Existing sessions continue to expiry; new handshakes fail closed | Specified |
| Keys | Never present in INV-20 configuration (`secret://` refs only), logs, or evidence | Enforced by config validation + redaction |

Required integration tests at the owning layer: valid chain, untrusted root, name mismatch, expired,
revoked (if enforced), unsupported version/cipher, missing/wrong mTLS identity, SNI/Host mismatch, and a
certificate-rotation drill. None can execute in this repository; component 7 stays **BLOCKED**.
