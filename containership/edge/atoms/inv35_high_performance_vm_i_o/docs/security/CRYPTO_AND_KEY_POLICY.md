# Encryption and key-rotation policy (C047, C039)

| Item | Policy |
|---|---|
| Sensitive data handled | capability tokens, MAC keys, evidence key; descriptor *contents* are never read by INV-35 |
| Payload encryption | INV-35 does not decrypt or inspect guest payloads; encryption in transit/at rest belongs to PLN-06/backends |
| Metadata protection | audit entries MACed; capabilities MACed; no secrets in config/logs (R-015) |
| Algorithms | HMAC-SHA-256 (≥256-bit keys), SHA-256 digests. No custom crypto. |
| Key storage | reference: in-process `KeyRing`; production: HSM/KMS, keys non-exportable |
| Rotation cadence | signing keys every 30 days or on suspicion; `KeyRing.rotate()` activates new key, old key verifies until `retire()` |
| Retirement | after max token TTL (≤ 1 h) past rotation; retirement flushes verification cache and invalidates outstanding tokens |
| Evidence key | `INV35_EVIDENCE_KEY` supplied by CI secret store only; never committed |
| Secrets in config | refused at load (E504); secrets are referenced by *handle* from a secret store, never inlined |
| Redaction | field-name based (`security.redact`), applied to logs, decisions and audit before storage |
| Compromise response | rotate + retire immediately; quarantine affected queues; see INCIDENT_RESPONSE.md SEV1 |
