# Key management — INV-42 (MC-018, MC-014, MC-015)

| Key | Where | Lifetime / rotation | Compromise response |
|---|---|---|---|
| Per-table HMAC key | Process memory (`bytearray`), random 256-bit, or from `key_provider` | Lives as long as the table session. To rotate, destroy the table and create a new one. Clients re-acquire descriptors. | `destroy()` the table. The blast radius is that one table (T8). |
| Audit MAC key | Held by the audit-sink operator and passed to `AuditLog(mac_key=)` | Rotate every 90 days by starting a new chain file that anchors the old head | Re-verify existing chains with the old key and start a new chain |
| Release signing key (Ed25519) | HSM/KMS signing service. Never stored on CI runners. | Rotate yearly. Publish the new public key and keep old keys for historical verification. | Revoke the key, publish the revocation, re-sign current releases with the new key, and follow INCIDENT_RUNBOOK SEV1 |
| Transport certificates | Deployment PKI (W-005) | At most 30 days, automated | Revoke through the CA. Pinned identities limit exposure. |

## Protected memory

CPython can't pin memory or guarantee zeroization. `destroy()` overwrites the key buffer as a best effort. A `key_provider` can supply a key from a KMS or TEE, but the key is still copied into the process. This residual risk is accepted under W-007. Hosts that need stronger guarantees should run on a confidential-compute VM.

## At rest

INV-42 persists no descriptor state. The audit log holds no secrets. Encryption at rest is therefore limited to the audit volume, which uses platform disk encryption.
