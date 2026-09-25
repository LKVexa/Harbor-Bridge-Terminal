# Threat model (M32, C041)

| Threat | Mitigation | Test |
|---|---|---|
| Malicious tenant uses another tenant's link | identity-scoped keys + signed identity | test_identity_binding |
| Link-name/separator confusion | tuple keys, JSON-encoded store keys | test_adversarial::link_confusion |
| Forged / replayed / malleable tokens | HMAC, nonce cache, canonical base64 | test_authentication, test_adversarial |
| Decision replay across links/ops | exact resource+op match | test_adversarial |
| Inline secret in config / leak via logs | validator + redaction + ref-only storage | test_secret_handling |
| Revoked link resurrected (restart/restore) | durable tombstones, restore guard | test_state_recovery |
| State tampering on disk | checksums, optional AES-GCM with AAD | test_state_recovery, test_key_rotation |
| Audit tampering | hash chain + head check | test_audit_chain |
| Untrusted provider implementation | digest allowlist | test_registry_negotiation |
| Resource exhaustion | bounds, quotas, admission, breaker | test_adversarial, Admission |
| Split-brain | lease epochs | test_failover_splitbrain |
| Residency violation on failover | residency engine | Residency tests |
| Plaintext interception | TLS 1.3 mTLS | TransportPolicy |

Out of scope here: side channels, sandbox escape (INV-60 host), kernel/device authority.
