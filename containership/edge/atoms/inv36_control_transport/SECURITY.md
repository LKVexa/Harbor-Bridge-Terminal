# Security model - INV-36 Control transport 5.1.0

## Boundary and components

| Layer | Protects | Module |
|---|---|---|
| PK_CTRL_STREAM/1 | bounded framing of an untrusted byte stream | `stream.py` |
| PK_CTRL_HS/1 | mutual authentication, forward-secret key agreement, identity/transcript binding | `handshake.py` |
| PK_CTRL_FRAME/2 | confidentiality, integrity, exact ordering, replay rejection per frame | `transport.py` |
| PK_CTRL_MSG/1 | canonical typed envelope; tenant/type/op_id authenticated inside the AEAD | `messages.py` |
| Authorization | least privilege per operation, tenant isolation, default deny | `policy.py` |
| Quarantine | emergency isolation, kill switch | `quarantine.py` |
| Audit | tamper-evident record of security decisions | `audit_log.py` |

## Threat model

Attacker capabilities considered:

| Attacker | Capabilities | Main mitigations |
|---|---|---|
| Hostile guest / compromised tenant workload | arbitrary bytes on its vsock connection; many connections; stalls; forged tenant IDs in messages | bounded records and handshake; churn/connection limits; penalty box; credential-bound tenant; authorization; quarantine |
| Hostile host process (without the host agent key) | connect to guests, replay recorded traffic | mutual authentication; fresh ephemerals; transcript-bound session ID; replay/sequence checks |
| Replaying / reordering / modifying relay (GAP-12 path) | observe, drop, duplicate, delay, reorder, modify ciphertext | AEAD; exact-next sequencing; relay has no keys; routing metadata never authorizes |
| MITM during establishment | substitute ephemerals, strip suites, splice transcripts | Ed25519 signatures over transcripts including offered suites; MAC key confirmation |
| Stale or revoked credential holder | present an old credential or old key epoch | validity window with bounded skew; revocation feed (fail closed when unavailable); epoch policy |
| Test/dev credential in production | cross-environment use | `env` namespace in credential must equal verifier environment; key-ref namespace checks |
| Time-service failure / manipulation | skewed or failing clock | clock validated before use; bounded skew; failure => `HS_DEPENDENCY` |
| Compromised policy/config source | push permissive policy or unsafe config | policy/config validation, rollback protection, wildcard approval requirement, audit |
| Log/telemetry reader | read sensitive data from logs/metrics | redaction, pseudonymized tenant IDs, no raw IDs as labels, secrets never logged |
| Insider tampering with audit log | delete/modify/reorder records | hash chain, signed checkpoints, external head |

Out of scope: a compromised host kernel/VMM (controls guest memory), side channels in the AES/X25519/Ed25519 implementations (delegated to OpenSSL via `cryptography`), denial of service by the hypervisor itself.

## What the hypervisor provides vs what is proven end-to-end

The VMM provides byte delivery and a CID. CIDs are **not** trusted for identity (reassigned on migration/restore, chosen by the VMM operator); they are used only for admission, churn limiting and quarantine scoping. Identity, tenant, role, environment and key epoch are proven cryptographically by PK_CTRL_HS/1.

## Cryptography

- PK_CTRL_HS/1: X25519 ephemeral ECDH, Ed25519 credentials and transcript signatures, HKDF-SHA-256 key schedule, HMAC-SHA-256 key confirmation (`docs/PROTOCOL.md`). **New construction - requires external cryptographic review before production (ADR-0001).**
- PK_CTRL_FRAME/2 (unchanged from 5.0.0): AES-256-GCM-SIV, HKDF-SHA-256 directional keys and nonce prefixes bound to session ID and identities; header authenticated; exact-next 64-bit sequence; fail closed before wrap.
- All randomness from the OS CSPRNG (`secrets`, `cryptography`).

## Fail-closed behaviour

Authentication, integrity, protocol and authorization failures never advance state or reach handlers; integrity failures close the channel. Unavailable identity/revocation/attestation/time/policy dependencies fail new sessions and operations closed. Unverifiable persisted quarantine state denies everything. Security-critical audit events that cannot be written block the action.

## Secret handling limitation

Python immutable byte strings and backend key objects cannot be reliably zeroized. INV-36 drops references (establishment secret after derivation, traffic keys on close, `SigningKey.destroy()`), refuses to pickle key handles and never logs key material - this is reference minimisation, not certified zeroization (debt D-001). Core dumps of agent processes must be treated as secret.

## Remaining security gaps (see `docs/MC_CHECKLIST_STATUS.md`)

External review of PK_CTRL_HS/1; production KMS/HSM `KeyProvider`; GAP-06 attestation integration; distributed quarantine propagation; WORM storage for audit segments; real-vsock certification rows; named security owner and vulnerability contact.

## Reporting vulnerabilities

Security contact: UNASSIGNED (`governance/owners.json`). Process and SLAs: `docs/GOVERNANCE.md`.
